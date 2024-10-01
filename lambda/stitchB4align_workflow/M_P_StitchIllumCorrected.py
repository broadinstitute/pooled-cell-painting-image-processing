import json
import os
import sys
import time
import numpy as np
import string
import posixpath

import boto3

sys.path.append("/opt/pooled-cell-painting-lambda")

import run_DCP
import helpful_functions

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Step Information
metadata_file_name = "/tmp/metadata.json"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "PROJECT_P_StitchIllumCorrected",
    "DOCKERHUB_TAG": "cellprofiler/distributed-fiji:latest",
    "SCRIPT_DOWNLOAD_URL": "https://raw.githubusercontent.com/broadinstitute/pooled-cell-painting-image-processing/refs/heads/alt_FIJI/FIJI/BatchStitchPooledCellPainting_Stitch_Headless.py",
    "TASKS_PER_MACHINE": "1",
    "MACHINE_TYPE": ["m5.2xlarge"],
    "TASKS_PER_MACHINE": "1",
    "MACHINE_TYPE": ["m5.2xlarge"],
    "MACHINE_PRICE": "0.25",
    "EBS_VOL_SIZE": "400",
    "DOWNLOAD_FILES": "False",
    "MEMORY": "31000",
    "SQS_MESSAGE_VISIBILITY": "43200",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
}

# List plates if you want to exclude them from run.
exclude_plates = []
# List plates if you want to only run them and exclude all others from run.
include_plates = []

class JobQueue:
    def __init__(self, name=None):
        self.sqs = boto3.resource("sqs")
        self.queue = self.sqs.get_queue_by_name(QueueName=name)
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print(("Batch sent. Message ID:", response.get("MessageId")))


def lambda_handler(event, context):
    # Log the received event
    bucket_name = event["bucket_name"]
    batch = event["batch"]
    image_prefix = event["image_prefix"]
    prefix = os.path.join(image_prefix, "workspace/")
    app_name = config_dict["APP_NAME"]

    # Get the metadata file
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print(f"Downloading metadata from {metadata_on_bucket_name}")
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    plate_and_well_list = metadata["painting_plate_and_well_list"]
    # Apply filters to active plate_and_well_list
    if exclude_plates:
        plate_and_well_list = [
            x for x in plate_and_well_list if x[0] not in exclude_plates
        ]
    if include_plates:
        plate_and_well_list = [x for x in plate_and_well_list if x[0] in include_plates]

    # Calculate EXPECTED_NUMBER_FILES per well
    number_channels = len(metadata["channel_list"])
    stitched_CP_files = stitched10X_CP_files = 4 * number_channels  # 4 quadrants
    expected_number_CP_files = (
        stitched_CP_files + stitched10X_CP_files
    )
    config_dict["EXPECTED_NUMBER_FILES"] = expected_number_CP_files

    
    # now let's do our stuff!
    run_DCP.run_setup(
        bucket_name, prefix, batch, config_dict, cellprofiler=False
    )
    
    
    # make the jobs
    tileperside=metadata["tileperside"]
    final_tile_size=metadata["final_tile_size"]
    xoffset_tiles=metadata["painting_xoffset_tiles"]
    yoffset_tiles=metadata["painting_yoffset_tiles"]
    compress=metadata["compress"]

    step_to_stitch = "images_illumcorrected"
    local_start_path = posixpath.join("/home/ubuntu/bucket", image_prefix)
    if "round_or_square" in list(metadata.keys()):
        round_or_square = metadata["round_or_square"]
    else:  # Backwards compatibility for old square runs
        round_or_square = "square"
    stitchqueue = JobQueue(app_name + "Queue")
    stitchMessage = {
        "Metadata": "",
        "output_file_location": posixpath.join(image_prefix, batch),
        "shared_metadata": {
            "input_file_location": local_start_path,
            "step_to_stitch": step_to_stitch,
            "scalingstring": "1",
            "overlap_pct": metadata["overlap_pct"],
            "size": "1480",
            "rows": metadata["painting_rows"],
            "columns": metadata["painting_columns"],
            "imperwell": metadata["painting_imperwell"],
            "stitchorder": "Grid=snake by rows",
            "channame": "DNA",
            "tileperside": str(tileperside),
            "awsdownload": "True",
            "bucketname": bucket_name,
            "localtemp": "local_temp",
            "round_or_square": round_or_square,
            "quarter_if_round": "True",
            "final_tile_size": str(final_tile_size),
            "xoffset_tiles": str(xoffset_tiles),
            "yoffset_tiles": str(yoffset_tiles),
            "compress": compress,
        },
    }
    for tostitch in plate_and_well_list:
        if "_" not in tostitch[1]:
            well = "Well_" + tostitch[1][4:]
        else:
            well = tostitch[1]
        stitchMessage["Metadata"] = {
            "subdir": posixpath.join(
                batch,
                step_to_stitch,
                "painting",
                tostitch[0] + "-" + tostitch[1],
            ),
            "out_subdir_tag": tostitch[0] + "_" + tostitch[1],
            "filterstring": well,
            "downloadfilter": "*" + well + "*",
        }
        stitchqueue.scheduleBatch(stitchMessage)
    print("Stitching job submitted. Check your queue")
    
    
    run_DCP.grab_batch_config(bucket_name, prefix, batch)
    # Start a cluster
    run_DCP.run_cluster(
        bucket_name, prefix, batch, len(plate_and_well_list), config_dict
    )

    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, "M_P_StitchIllumCorrected", config_dict)
    print("Go run the monitor now")
    return "Cluster started"
    
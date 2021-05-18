import json
import os
import sys
import time
import numpy as np
import boto3

sys.path.append("/opt/pooled-cell-painting-lambda")

import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Step Information
metadata_file_name = "/tmp/metadata.json"
step = "8"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_BarcodingStitching",
    "DOCKERHUB_TAG": "cellprofiler/distributed-fiji:latest",
    "SCRIPT_DOWNLOAD_URL": "https://raw.githubusercontent.com/broadinstitute/pooled-cell-painting-image-processing/master/FIJI/BatchStitchPooledCellPainting_StitchAndCrop_Headless.py",
    "MACHINE_TYPE": "m4.2xlarge",
    "MACHINE_PRICE": "0.25",
    "EBS_VOL_SIZE": "800",
    "DOWNLOAD_FILES": "False",
    "MEMORY": "31000",
    "SQS_MESSAGE_VISIBILITY": "10800",
    "EXPECTED_NUMBER_FILES": "3996",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
}


def lambda_handler(event, context):
    # Set up for Manual Trigger
    bucket_name = "pooled-cell-painting"
    image_prefix = "projects/2018_11_20_Periscope_X/"
    batch = "nameofthebatch"
    prefix = "projects/2018_11_20_Periscope_X/workspace/"

    print(plate, batch, image_prefix, prefix)

    # get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print("Loading", metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    image_dict = metadata["barcoding_file_data"]
    num_series = int(metadata["barcoding_rows"]) * int(metadata["barcoding_columns"])
    if metadata["barcoding_imperwell"] != "":
        if int(metadata["barcoding_imperwell"]) != 0:
            num_series = int(metadata["barcoding_imperwell"])
    # number of site * 4 channels barcoding * number of cycles. doesn't include 1 DAPI/site
    expected_files_per_well = int(num_series) * 4 * int(metadata["barcoding_cycles"])
    plate_and_well_list = metadata["barcoding_plate_and_well_list"]

    # Removed Check if Run Done
    # now let's do our stuff!
    app_name = run_DCP.run_setup(
        bucket_name, prefix, batch, config_dict, cellprofiler=False
    )

    # make the jobs
    create_batch_jobs.create_batch_jobs_8Z(
        bucket_name,
        image_prefix,
        batch,
        metadata,
        plate_and_well_list,
        app_name,
        tileperside=metadata["tileperside"],
        final_tile_size=metadata["final_tile_size"],
        xoffset_tiles=metadata["barcoding_xoffset_tiles"],
        yoffset_tiles=metadata["barcoding_yoffset_tiles"],
        compress=metadata["compress"],
    )

    # Start a cluster
    run_DCP.run_cluster(
        bucket_name, prefix, batch, len(plate_and_well_list, config_dict)
    )

    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, step, config_dict)
    print("Go run the monitor now")
    return "Cluster started"

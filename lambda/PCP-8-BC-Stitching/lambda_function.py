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

# Step Information
metadata_file_name = "/tmp/metadata.json"
step = "8"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_BarcodingStitching",
    "DOCKERHUB_TAG": "cellprofiler/distributed-fiji:latest",
    "SCRIPT_DOWNLOAD_URL": "https://raw.githubusercontent.com/broadinstitute/pooled-cell-painting-image-processing/master/FIJI/BatchStitchPooledCellPainting_StitchAndCrop_Headless.py",
    "TASKS_PER_MACHINE": "1",
    "MACHINE_TYPE": ["m4.2xlarge"],
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
    # Log the received event
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    keys = [x["s3"]["object"]["key"] for x in event["Records"]]
    plate = key.split("/")[-2].split("-")[0]
    batch = key.split("/")[-5]
    image_prefix = key.split(batch)[0]
    prefix = os.path.join(image_prefix, "workspace/")

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

    # First let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    filter_prefix = image_prefix + batch + "/images_corrected/barcoding"
    # Because this step is batched per site (not well) don't need to anticipate partial loading of jobs
    expected_len = int(len(plate_and_well_list)) * int(expected_files_per_well) + 5

    done = helpful_functions.check_if_run_done(
        s3,
        bucket_name,
        filter_prefix,
        expected_len,
        current_app_name,
        prev_step_app_name,
        sqs,
        duplicate_queue_name,
    )

    if not done:
        print("Still work ongoing")
        return "Still work ongoing"
    else:
        # now let's do our stuff!
        app_name = run_DCP.run_setup(
            bucket_name, prefix, batch, config_dict, cellprofiler=False
        )

        # make the jobs
        create_batch_jobs.create_batch_jobs_8(
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

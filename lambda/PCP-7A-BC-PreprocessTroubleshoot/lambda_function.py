import json
import os
import sys
import time
import boto3

sys.path.append("/opt/pooled-cell-painting-lambda")

import create_CSVs
import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Step information
metadata_file_name = "/tmp/metadata.json"
pipeline_name = "7_BC_Preprocess_Troubleshoot.cppipe"
step = "7A"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_PreprocessBarcodingTroubleshoot",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.1.3",
    "TASKS_PER_MACHINE": "2",
    "MACHINE_TYPE": ["r4.2xlarge"],
    "MACHINE_PRICE": "0.40",
    "EBS_VOL_SIZE": "800",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "2",
    "MEMORY": "30000",
    "SECONDS_TO_START": "180",
    "SQS_MESSAGE_VISIBILITY": "7200",
    "CHECK_IF_DONE_BOOL": "True",
    "EXPECTED_NUMBER_FILES": "49",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
}


def lambda_handler(event, context):
    # Log the received event
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    keys = [x["s3"]["object"]["key"] for x in event["Records"]]
    batch = key.split("/")[-2]
    image_prefix = key.split("workspace")[0]
    prefix = os.path.join(image_prefix, "workspace/")

    # Load metadata file
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print(f"Downloading metadata from {metadata_on_bucket_name}")
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )
    plate_and_well_list = metadata["barcoding_plate_and_well_list"]
    image_dict = metadata["wells_with_all_cycles"]
    expected_cycles = metadata["barcoding_cycles"]
    platelist = list(image_dict.keys())
    num_series = int(metadata["barcoding_rows"]) * int(metadata["barcoding_columns"])
    if metadata["barcoding_imperwell"] != "":
        if int(metadata["barcoding_imperwell"]) != 0:
            num_series = int(metadata["barcoding_imperwell"])
    expected_files_per_well = (
        num_series * ((int(metadata["barcoding_cycles"]) * 4) + 1)
    ) + 3
    num_sites = round(len(plate_and_well_list) * num_series / skip)

    # Setup DCP
    app_name = run_DCP.run_setup(bucket_name, prefix, batch, config_dict)

    # Make the jobs
    create_batch_jobs.create_batch_jobs_7A(
        image_prefix,
        batch,
        pipeline_name,
        plate_and_well_list,
        list(range(num_series)),
        app_name,
        skip,
    )

    # Start a cluster
    run_DCP.run_cluster(bucket_name, prefix, batch, num_sites, config_dict)

    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, step, config_dict)
    print("Go run the monitor now")

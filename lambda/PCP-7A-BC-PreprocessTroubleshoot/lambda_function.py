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
pipeline_name = "7A_BC_PreprocessTroubleshoot.cppipe"
metadata_file_name = "/tmp/metadata.json"
fleet_file_name = "preprocessFleet.json"
step = "7A"
skip = 15  # Must match skip set in config file


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
    print("Loading", metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )
    plate_and_well_list = metadata["barcoding_plate_and_well_list"]
    image_dict = metadata["wells_with_all_cycles"]
    expected_cycles = metadata["barcoding_cycles"]
    platelist = list(image_dict.keys())
    num_series = int(metadata["barcoding_rows"]) * int(metadata["barcoding_columns"])
    if "barcoding_imperwell" in list(metadata.keys()):
        if metadata["barcoding_imperwell"] != "":
            if int(metadata["barcoding_imperwell"]) != 0:
                num_series = int(metadata["barcoding_imperwell"])
    expected_files_per_well = (
        num_series * ((int(metadata["barcoding_cycles"]) * 4) + 1)
    ) + 3
    num_sites = round(len(plate_and_well_list) * num_series / skip)

    # Setup DCP
    app_name = run_DCP.run_setup(bucket_name, prefix, batch)

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
    run_DCP.run_cluster(bucket_name, prefix, batch, step, fleet_file_name, num_sites)

    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, step)
    print("Go run the monitor now")

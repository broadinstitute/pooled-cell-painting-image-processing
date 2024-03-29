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
pipeline_name = "7_BC_Preprocess.cppipe"
step = "7"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_PreprocessBarcoding",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.2.1",
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

# List plates if you want to exclude them from run.
exclude_plates = []
# List plates if you want to only run them and exclude all others from run.
include_plates = []


def lambda_handler(event, context):
    # Log the received event
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    keys = [x["s3"]["object"]["key"] for x in event["Records"]]
    if ".cppipe" not in key:
        plate = key.split("/")[-2].split("_")[0]
        batch = key.split("/")[-5]
        image_prefix = key.split(batch)[0]
        print(plate)
    else:
        batch = key.split("/")[-2]
        image_prefix = key.split("workspace")[0]
    prefix = os.path.join(image_prefix, "workspace/")

    print(f"Batch is {batch}\n Image prefix is {image_prefix}\n Prefix is {prefix}")

    # Check that the barcodes.csv is present
    barcodepath = os.path.join(prefix, "metadata", batch)
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=barcodepath)
    filelist = []
    for obj in response.get("Contents", []):
        filelist.append(obj["Key"])
    if not any(".csv" in file for file in filelist):
        print(f"No Barcodes.csv in {barcodepath}")
        return "Barcodes.csv is missing"

    # Get the metadata file
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print(f"Downloading metadata from {metadata_on_bucket_name}")
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    plate_and_well_list = metadata["barcoding_plate_and_well_list"]
    image_dict = metadata["wells_with_all_cycles"]
    expected_cycles = metadata["barcoding_cycles"]
    platelist = list(image_dict.keys())
    # Apply filters to plate and well lists
    if exclude_plates:
        platelist = [i for i in platelist if i not in exclude_plates]
        plate_and_well_list = [
            x for x in plate_and_well_list if x[0] not in exclude_plates
        ]
    if include_plates:
        platelist = include_plates
        plate_and_well_list = [x for x in plate_and_well_list if x[0] in include_plates]

    num_series = int(metadata["barcoding_rows"]) * int(metadata["barcoding_columns"])
    if metadata["barcoding_imperwell"] != "":
        if int(metadata["barcoding_imperwell"]) != 0:
            num_series = int(metadata["barcoding_imperwell"])
    expected_files_per_well = (
        num_series * ((int(metadata["barcoding_cycles"]) * 4) + 1)
    ) + 3
    num_sites = len(plate_and_well_list) * num_series

    # First let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    run_DCP.grab_batch_config(bucket_name, prefix, batch)
    from configAWS import SQS_DUPLICATE_QUEUE

    filter_prefix = image_prefix + batch + "/images_aligned/barcoding"
    # Expected length shows that all transfers (i.e. all wells) have at least started
    expected_len = ((len(plate_and_well_list) - 1) * expected_files_per_well) + 1

    print("Checking if all files are present")
    prev_step_app_name = (
        config_dict["APP_NAME"].rsplit("_", 1)[-2] + "_ApplyIllumBarcoding"
    )
    done = helpful_functions.check_if_run_done(
        s3,
        bucket_name,
        filter_prefix,
        expected_len,
        config_dict["APP_NAME"],
        prev_step_app_name,
        sqs,
        SQS_DUPLICATE_QUEUE,
    )

    if not done:
        print("Still work ongoing")
        return "Still work ongoing"
    else:
        # Pull the file names we care about, and make the CSV
        for eachplate in platelist:
            platedict = image_dict[eachplate]
            well_list = list(platedict["1"].keys())
            bucket_folder = (
                "/home/ubuntu/bucket/"
                + image_prefix
                + batch
                + "/images_aligned/barcoding"
            )
            per_plate_csv = create_CSVs.create_CSV_pipeline7(
                eachplate, num_series, expected_cycles, bucket_folder, well_list
            )
            csv_on_bucket_name = (
                prefix
                + "load_data_csv/"
                + batch
                + "/"
                + eachplate
                + "/load_data_pipeline7.csv"
            )
            print(f"Created {csv_on_bucket_name}")
            with open(per_plate_csv, "rb") as a:
                s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)

        # now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name, prefix, batch, config_dict)

        # make the jobs
        create_batch_jobs.create_batch_jobs_7(
            image_prefix,
            batch,
            pipeline_name,
            plate_and_well_list,
            list(range(num_series)),
            app_name,
        )

        # Start a cluster
        run_DCP.run_cluster(bucket_name, prefix, batch, num_sites, config_dict)

        # Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch, step, config_dict)
        print("Go run the monitor now")
        return "Cluster started"

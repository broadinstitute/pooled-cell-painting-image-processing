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
pipeline_name = "9_Analysis.cppipe"
step = "9"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_Analysis",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.2.1",
    "TASKS_PER_MACHINE": "1",
    "MACHINE_TYPE": ["m5.4xlarge"],
    "MACHINE_PRICE": "0.50",
    "EBS_VOL_SIZE": "60",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "1",
    "MEMORY": "62500",
    "SECONDS_TO_START": "600",
    "SQS_MESSAGE_VISIBILITY": "28800",
    "CHECK_IF_DONE_BOOL": "True",
    "EXPECTED_NUMBER_FILES": "5",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
}

# List plates if you want to exclude them from run.
exclude_plates = []
# List plates if you want to only run them and exclude all others from run.
include_plates = []


def lambda_handler(event, context):
    # Manual trigger
    batch = "BATCH_STRING"
    image_prefix = "projects/2018_11_20_Periscope_X/"
    prefix = "projects/2018_11_20_Periscope_X/workspace/"
    bucket_name = "BUCKET"

    # Get the metadata file
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print(f"Downloading metadata from {metadata_on_bucket_name}")
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )
    image_dict = metadata["wells_with_all_cycles"]
    platelist = list(image_dict.keys())
    plate_and_well_list = metadata["barcoding_plate_and_well_list"]
    # Apply filters to plate and well lists
    if exclude_plates:
        platelist = [i for i in platelist if i not in exclude_plates]
        plate_and_well_list = [
            x for x in plate_and_well_list if x[0] not in exclude_plates
        ]
    if include_plates:
        platelist = include_plates
        plate_and_well_list = [x for x in plate_and_well_list if x[0] in include_plates]

    expected_cycles = metadata["barcoding_cycles"]
    num_sites_perwell = int(metadata["tileperside"]) ** 2
    num_sites_total = len(plate_and_well_list) * num_sites_perwell

    # Pull the file names we care about, and make the CSV
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = list(platedict["1"].keys())
        bucket_folder = (
            "/home/ubuntu/bucket/" + image_prefix + batch + "/images_corrected_cropped"
        )
        per_plate_csv = create_CSVs.create_CSV_pipeline9(
            eachplate, num_sites_perwell, expected_cycles, bucket_folder, well_list
        )
        csv_on_bucket_name = (
            prefix
            + "load_data_csv/"
            + batch
            + "/"
            + eachplate
            + "/load_data_pipeline9.csv"
        )
        print("Created", csv_on_bucket_name)
        with open(per_plate_csv, "rb") as a:
            s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)

    # now let's do our stuff!
    app_name = run_DCP.run_setup(bucket_name, prefix, batch, config_dict)

    # make the jobs
    create_batch_jobs.create_batch_jobs_9(
        image_prefix,
        batch,
        pipeline_name,
        plate_and_well_list,
        list(range(1, num_sites_perwell + 1)),
        app_name,
    )

    # Start a cluster
    run_DCP.run_cluster(bucket_name, prefix, batch, num_sites_total, config_dict)

    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, step, config_dict)
    print("Go run the monitor now")
    return "Cluster started"

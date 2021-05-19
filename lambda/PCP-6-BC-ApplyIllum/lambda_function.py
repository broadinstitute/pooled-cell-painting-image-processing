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
pipeline_name = "6_BC_Apply_Illum.cppipe"
step = "6"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_ApplyIllumBarcoding",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.1.3",
    "TASKS_PER_MACHINE":"2",
    "MACHINE_TYPE": ["r4.2xlarge"],
    "MACHINE_PRICE": "0.40",
    "EBS_VOL_SIZE": "800",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "2",
    "MEMORY": "30000",
    "SECONDS_TO_START": "180",
    "SQS_MESSAGE_VISIBILITY": "43200",
    "CHECK_IF_DONE_BOOL": "False",
    "EXPECTED_NUMBER_FILES": "5",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
}


def lambda_handler(event, context):
    # Log the received event
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    keys = [x["s3"]["object"]["key"] for x in event["Records"]]
    plate = key.split("/")[-2]
    batch = key.split("/")[-4]
    image_prefix = key.split(batch)[0]
    prefix = os.path.join(image_prefix, "workspace/")

    # get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print("Loading", metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    image_dict = metadata["wells_with_all_cycles"]
    num_series = int(metadata["barcoding_rows"]) * int(metadata["barcoding_columns"])
    if metadata["barcoding_imperwell"] != "":
        if int(metadata["barcoding_imperwell"]) != 0:
            num_series = int(metadata["barcoding_imperwell"])
    expected_cycles = int(metadata["barcoding_cycles"])
    platelist = list(image_dict.keys())

    # Default pipeline is slow. If images acquired in fast mode, pulls alternate pipeline.
    pipe_name = pipeline_name
    if metadata["fast_or_slow_mode"] == "fast":
        if "fast" not in pipe_name:
            pipe_name = pipe_name[:-7] + "_fast.cppipe"
    print(f"Pipeline name is {pipe_name}")

    # First let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    filter_prefix = image_prefix + batch + "/illum"
    expected_len = int(metadata["barcoding_cycles"]) * len(platelist) * 5

    done = helpful_functions.check_if_run_done(
        s3,
        bucket_name,
        filter_prefix,
        expected_len,
        current_app_name,
        prev_step_app_name,
        sqs,
        duplicate_queue_name,
        filter_in="Cycle",
    )

    if not done:
        print("Still work ongoing")
        return "Still work ongoing"
    else:
        # First thing first, let's make an easier-to-use plate and well list and save it
        plate_and_well_list = []
        for eachplate in platelist:
            platedict = image_dict[eachplate]
            well_list = list(platedict["1"].keys())
            for eachwell in well_list:
                plate_and_well_list.append((eachplate, eachwell))
        metadata["barcoding_plate_and_well_list"] = plate_and_well_list
        helpful_functions.write_metadata_file(
            s3, bucket_name, metadata, metadata_file_name, metadata_on_bucket_name
        )
        # Pull the file names we care about, and make the CSV
        for eachplate in platelist:
            platedict = image_dict[eachplate]
            bucket_folder = (
                "/home/ubuntu/bucket/" + image_prefix + batch + "/images/" + eachplate
            )
            illum_folder = (
                "/home/ubuntu/bucket/" + image_prefix + batch + "/illum/" + eachplate
            )
            per_plate_csv = create_CSVs.create_CSV_pipeline6(
                eachplate,
                num_series,
                expected_cycles,
                bucket_folder,
                illum_folder,
                platedict,
                metadata["one_or_many_files"],
                metadata["fast_or_slow_mode"],
            )
            csv_on_bucket_name = (
                prefix
                + "load_data_csv/"
                + batch
                + "/"
                + eachplate
                + "/load_data_pipeline6.csv"
            )
            print("Created", csv_on_bucket_name)
            with open(per_plate_csv, "rb") as a:
                s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)

        # now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name, prefix, batch, config_dict)

        # make the jobs
        create_batch_jobs.create_batch_jobs_6(
            image_prefix,
            batch,
            pipe_name,
            plate_and_well_list,
            app_name,
            metadata["one_or_many_files"],
            num_series,
        )

        # Start a cluster
        if metadata["one_or_many_files"] == "one":
            njobs = len(plate_and_well_list) * 19
        else:
            njobs = len(plate_and_well_list) * num_series
        run_DCP.run_cluster(bucket_name, prefix, batch, njobs, config_dict)

        # Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch, step, config_dict)
        print("Go run the monitor now")
        return "Cluster started"

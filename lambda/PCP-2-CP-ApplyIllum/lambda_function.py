import json
import os
import sys
import time
import boto3

sys.path.append("/opt/pooled-cell-painting-lambda")

import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Step information
metadata_file_name = "/tmp/metadata.json"
step = "2"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_ApplyIllumPainting",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.1.3",
    "MACHINE_TYPE": "m4.2xlarge",
    "MACHINE_PRICE": "0.25",
    "EBS_VOL_SIZE": "350",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "1",
    "MEMORY": "30000",
    "SECONDS_TO_START": "3 * 60",
    "SQS_MESSAGE_VISIBILITY": "720 * 60",
    "CHECK_IF_DONE_BOOL": "True",
    "EXPECTED_NUMBER_FILES": "5000",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
    "USE_PLUGINS": "True",
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

    # Get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    image_dict = metadata["painting_file_data"]
    # Calculate number of images from rows and columns in metadata
    num_series = int(metadata["painting_rows"]) * int(metadata["painting_columns"])
    # Overwrite rows x columns number series if images per well set in metadata
    if "painting_imperwell" in list(metadata.keys()):
        if metadata["painting_imperwell"] != "":
            if int(metadata["painting_imperwell"]) != 0:
                num_series = int(metadata["painting_imperwell"])

    # Standard vs. SABER configs
    if "Channeldict" not in list(metadata.keys()):
        print("Update your metadata.json to include Channeldict")
        return "Update your metadata.json to include Channeldict"
    Channeldict = ast.literal_eval(metadata["Channeldict"])
    if len(Channeldict.keys()) == 1:
        SABER = False
        print("Not a SABER experiment")
    if len(Channeldict.keys()) > 1:
        SABER = True
        print("SABER experiment")

    platelist = list(image_dict.keys())
    platedict = image_dict[plate]
    well_list = list(platedict.keys())

    # Now let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    filter_prefix = image_prefix + batch + "/illum"
    expected_len = (int(metadata["painting_channels"]) + 1) * len(platelist)

    done = helpful_functions.check_if_run_done(
        s3,
        bucket_name,
        filter_prefix,
        expected_len,
        current_app_name,
        prev_step_app_name,
        sqs,
        duplicate_queue_name,
        filter_out="Cycle",
    )

    if not done:
        print("Still work ongoing")
        return "Still work ongoing"

    else:
        # now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name, prefix, batch, step)

        if not SABER:
            pipeline_name = "2_CP_Apply_Illum.cppipe"
        if SABER:
            pipeline_name = "2_SABER_CP_Apply_Illum.cppipe"
        # make the jobs
        create_batch_jobs.create_batch_jobs_2(
            image_prefix, batch, pipeline_name, platelist, well_list, app_name
        )

        # Start a cluster
        run_DCP.run_cluster(
            bucket_name,
            prefix,
            batch,
            step,
            fleet_file_name,
            len(platelist) * len(well_list),
        )

        # Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch, step)
        print("Go run the monitor now")
        return "Cluster started"

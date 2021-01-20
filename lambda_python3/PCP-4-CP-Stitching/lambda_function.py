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
metadata_file_name = "/tmp/metadata.json"
fleet_file_name = "stitchFleet.json"
current_app_name = "2018_11_20_Periscope_X_PaintingStitching"
prev_step_app_name = "2018_11_20_Periscope_X_PaintingSegmentationCheck"
prev_step_num = "3"
duplicate_queue_name = "2018_11_20_Periscope_PreventOverlappingStarts.fifo"
step = "4"
# Make sure that range_skip matches that set in 2_3_cellpainting_segmentation_check lambda function
range_skip = 16
tileperside = 10
final_tile_size = 5500


def lambda_handler(event, context):
    # Log the received event
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    keys = [x["s3"]["object"]["key"] for x in event["Records"]]
    plate = key.split("/")[-2].split("-")[0]
    batch = key.split("/")[-4]
    image_prefix = key.split(batch)[0]
    prefix = os.path.join(image_prefix, "workspace/")

    print(plate, batch, image_prefix, prefix)

    # get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print("Loading", metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    image_dict = metadata["painting_file_data"]
    num_series = int(metadata["painting_rows"]) * int(metadata["painting_columns"])
    if "painting_imperwell" in list(metadata.keys()):
        if metadata["painting_imperwell"] != "":
            if int(metadata["painting_imperwell"]) != 0:
                num_series = int(metadata["painting_imperwell"])
    expected_files_per_well = np.ceil(float(num_series) / range_skip)
    plate_and_well_list = metadata["painting_plate_and_well_list"]

    # First let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    filter_prefix = image_prefix + batch + "/images_corrected/painting"
    # Because this step is batched per site (not well) don't need anticipate partial loading of jobs
    expected_len = (len(plate_and_well_list) * expected_files_per_well) + (
        6 * (len(platelist))
    )

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
        # first let's just try to run the monitor on the last step, in case we haven't yet
        helpful_functions.try_a_shutdown(
            s3, bucket_name, prefix, batch, prev_step_num, prev_step_app_name
        )

        # now let's do our stuff!
        app_name = run_DCP.run_setup(
            bucket_name, prefix, batch, step, cellprofiler=False
        )

        # make the jobs
        create_batch_jobs.create_batch_jobs_4(
            image_prefix,
            batch,
            metadata,
            plate_and_well_list,
            app_name,
            tileperside=tileperside,
            final_tile_size=final_tile_size,
        )

        # Start a cluster
        run_DCP.run_cluster(
            bucket_name, prefix, batch, step, fleet_file_name, len(plate_and_well_list)
        )

        # Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch, step)
        print("Go run the monitor now")
        return "Cluster started"

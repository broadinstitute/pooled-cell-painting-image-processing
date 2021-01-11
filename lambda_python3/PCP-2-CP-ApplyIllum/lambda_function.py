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
pipeline_name = "2_Apply_Illum_forCP_TI2.cppipe"
metadata_file_name = "/tmp/metadata.json"
fleet_file_name = "illumFleet.json"
prev_step_num = "1"
current_app_name = "2018_11_20_Periscope_X_ApplyIllumPainting"
prev_step_app_name = "2018_11_20_Periscope_X_IllumPainting"
duplicate_queue_name = "2018_11_20_Periscope_PreventOverlappingStarts.fifo"
step = "2"


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
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    image_dict = metadata["painting_file_data"]
    num_series = int(metadata["painting_rows"]) * int(metadata["painting_columns"])
    if "painting_imperwell" in list(metadata.keys()):
        if metadata["painting_imperwell"] != "":
            if int(metadata["painting_imperwell"]) != 0:
                num_series = int(metadata["painting_imperwell"])

    # Pull the file names we care about, and make the CSV
    platelist = list(image_dict.keys())
    plate = key.split("/")[-2]
    platedict = image_dict[plate]
    well_list = list(platedict.keys())
    paint_cycle_name = list(platedict[well_list[0]].keys())[0]
    per_well_im_list = []
    if metadata["one_or_many_files"] == "one":
        full_well_files = 1
    else:
        full_well_files = num_series
    full_well_list = []
    for eachwell in well_list:
        per_well = platedict[eachwell][paint_cycle_name]
        if len(per_well) == full_well_files:  # only keep full wells
            per_well_im_list.append(per_well)
            full_well_list.append(eachwell)
            print(("Added well", eachwell))
    bucket_folder = (
        "/home/ubuntu/bucket/"
        + image_prefix
        + batch
        + "/images/"
        + plate
        + "/"
        + paint_cycle_name
    )
    illum_folder = "/home/ubuntu/bucket/" + image_prefix + batch + "/illum/" + plate
    per_plate_csv = create_CSVs.create_CSV_pipeline2(
        plate,
        num_series,
        bucket_folder,
        illum_folder,
        per_well_im_list,
        full_well_list,
        metadata["one_or_many_files"],
    )
    csv_on_bucket_name = (
        prefix + "load_data_csv/" + batch + "/" + plate + "/load_data_pipeline2.csv"
    )
    print(csv_on_bucket_name)
    with open(per_plate_csv, "rb") as a:
        s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)

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

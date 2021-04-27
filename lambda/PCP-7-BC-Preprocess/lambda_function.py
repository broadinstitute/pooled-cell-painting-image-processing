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
pipeline_name = "7_BC_Preprocess.cppipe"
metadata_file_name = "/tmp/metadata.json"
fleet_file_name = "preprocessFleet.json"
current_app_name = "2018_11_20_Periscope_X_PreprocessBarcoding"
prev_step_app_name = "2018_11_20_Periscope_X_ApplyIllumBarcoding"
prev_step_num = "6"
duplicate_queue_name = "2018_11_20_Periscope_PreventOverlappingStarts.fifo"
step = "7"


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
    for obj in response.get('Contents', []):
        filelist += obj
    if ".csv" not in filelist:
        print (f"No Barcodes.csv in {barcodepath}")
        return("Barcodes.csv is missing")

    # get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print(("Loading", metadata_on_bucket_name))
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
    num_sites = len(plate_and_well_list) * num_series

    # First let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    filter_prefix = image_prefix + batch + "/images_aligned/barcoding"
    # Expected length shows that all transfers (i.e. all wells) have at least started
    expected_len = ((len(plate_and_well_list) - 1) * expected_files_per_well) + 1

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
            print(("Created", csv_on_bucket_name))
            with open(per_plate_csv, "rb") as a:
                s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)

        # now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name, prefix, batch, step)

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
        run_DCP.run_cluster(
            bucket_name, prefix, batch, step, fleet_file_name, num_sites
        )

        # Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch, step)
        print("Go run the monitor now")
        return "Cluster started"

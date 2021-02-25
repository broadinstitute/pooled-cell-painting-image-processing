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
pipeline_name = "9_Analysis.cppipe"
metadata_file_name = "/tmp/metadata.json"
fleet_file_name = "analysisFleet.json"
current_app_name = "2018_11_20_Periscope_X_Analysis"
step = "9"
num_tiles = 100  # set in steps 4 and 8

def lambda_handler(event, context):
    # Manual trigger
    batch = '20210124_6W_CP228/'
    image_prefix = '2018_11_20_Periscope_X'
    prefix = '2018_11_20_Periscope_X/workspace'
    bucket_name = 'imaging-platform'

    # get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print("Loading", metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    plate_and_well_list = metadata["barcoding_plate_and_well_list"]
    image_dict = metadata["wells_with_all_cycles"]
    expected_cycles = metadata["barcoding_cycles"]
    platelist = list(image_dict.keys())
    num_sites = int(num_tiles)

    # Pull the file names we care about, and make the CSV
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = list(platedict["1"].keys())
        bucket_folder = (
            "/home/ubuntu/bucket/" + image_prefix + batch + "/images_corrected_cropped"
        )
        per_plate_csv = create_CSVs.create_CSV_pipeline9(
            eachplate, num_sites, expected_cycles, bucket_folder, well_list
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
    app_name = run_DCP.run_setup(bucket_name, prefix, batch, step)

    # make the jobs
    create_batch_jobs.create_batch_jobs_9(
        image_prefix,
        batch,
        pipeline_name,
        plate_and_well_list,
        list(range(1, num_sites + 1)),
        app_name,
    )

    # Start a cluster
    run_DCP.run_cluster(bucket_name, prefix, batch, step, fleet_file_name, num_sites)

    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, step)
    print("Go run the monitor now")
    return "Cluster started"

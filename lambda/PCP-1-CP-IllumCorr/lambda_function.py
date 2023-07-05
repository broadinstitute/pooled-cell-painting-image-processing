import json
import os
import sys
import boto3
import ast

sys.path.append("/opt/pooled-cell-painting-lambda")

import create_CSVs
import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client("s3")

# Step information
metadata_file_name = "/tmp/metadata.json"
step = "1"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_IllumPainting",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.2.1",
    "TASKS_PER_MACHINE": "1",
    "MACHINE_TYPE": ["c5.xlarge"],
    "MACHINE_PRICE": "0.15",
    "EBS_VOL_SIZE": "22",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "4",
    "MEMORY": "7500",
    "SECONDS_TO_START": "180",
    "SQS_MESSAGE_VISIBILITY": "7200",
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
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    prefix, batchAndPipe = key.split("pipelines/")
    image_prefix = prefix.split("workspace")[0]
    batch = batchAndPipe.split("1_")[0][:-1]

    # Get the metadata file
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket, metadata_file_name, metadata_on_bucket_name
    )
    # Standard vs. SABER configs
    Channeldict = ast.literal_eval(metadata["Channeldict"])
    if len(Channeldict.keys()) == 1:
        SABER = False
        print("Not a SABER experiment")
    if len(Channeldict.keys()) > 1:
        SABER = True
        print("SABER experiment")

    # Calculate number of images from rows and columns in metadata
    num_series = int(metadata["painting_rows"]) * int(metadata["painting_columns"])
    # Overwrite rows x columns number series if images per well set in metadata
    if metadata["painting_imperwell"] != "":
        if int(metadata["painting_imperwell"]) != 0:
            num_series = int(metadata["painting_imperwell"])

    # Get the list of images in this experiment
    if not SABER:
        parse_name_filter = "20X_CP_"
    if SABER:
        parse_name_filter = ""
    image_list_prefix = image_prefix + batch + "/images/"
    image_list = helpful_functions.paginate_a_folder(s3, bucket, image_list_prefix)
    image_dict = helpful_functions.parse_image_names(
        image_list, filter_in=parse_name_filter, filter_out="copy"
    )
    metadata["painting_file_data"] = image_dict
    if len(image_dict) < 1:
        print ("Didn't find images. Confirm your file structure in S3 is correct.")
        return

    # Get the final list of channels in this experiment
    Channelrounds = list(Channeldict.keys())
    channels = []
    for eachround in Channelrounds:
        templist = []
        templist += Channeldict[eachround].values()
        channels += list(i[0] for i in templist)
    for index, chan in enumerate(channels):
        if "round" in chan:
            if "round0" in chan:
                channels[index] = chan.split("_")[0]
            else:
                channels.remove(chan)
    metadata["channel_list"] = channels

    # Add image list and channel list to metadata file
    helpful_functions.write_metadata_file(
        s3, bucket, metadata, metadata_file_name, metadata_on_bucket_name
    )

    # How many files/well indicates the well has all images present
    if metadata["one_or_many_files"] == "one":
        full_well_files = 1
    else:
        full_well_files = num_series

    platelist = list(image_dict.keys())
    # Apply filters to platelist
    if exclude_plates:
        platelist = [i for i in platelist if i not in exclude_plates]
    if include_plates:
        platelist = include_plates
    # Pull the file names we care about, and make the CSV
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = list(platedict.keys())
        # Only keep full wells
        print(f"{full_well_files} expected files per well and round for {eachplate}")
        incomplete_wells = []
        for eachwell in well_list:
            if SABER:
                for eachround in Channelrounds:
                    per_well = platedict[eachwell][eachround]
                    if len(per_well) != full_well_files:
                        incomplete_wells.append(eachwell)
                        print(
                            f"{eachwell} {eachround} doesn't have full well files. {len(per_well)} files found."
                        )
            if not SABER:
                paint_cycle_name = list(platedict[well_list[0]].keys())[0]
                per_well = platedict[eachwell][paint_cycle_name]
                if len(per_well) != full_well_files:
                    incomplete_wells.append(eachwell)
                    print(
                        f"{eachwell} {eachround} doesn't have full well files. {len(per_well)} files found."
                    )
        if incomplete_wells:
            for well in incomplete_wells:
                del platedict[well]
        bucket_folder = f"/home/ubuntu/bucket/{image_prefix}{batch}/images/{eachplate}/"
        illum_folder = f"/home/ubuntu/bucket/{image_prefix}{batch}/illum/{eachplate}/"
        per_plate_csv, per_plate_csv_2 = create_CSVs.create_CSV_pipeline1(
            eachplate,
            num_series,
            bucket_folder,
            illum_folder,
            platedict,
            metadata["one_or_many_files"],
            metadata["Channeldict"],
        )
        csv_on_bucket_name = f"{prefix}load_data_csv/{batch}/{eachplate}/load_data_pipeline1.csv"
        csv_on_bucket_name_2 = f"{prefix}load_data_csv/{batch}/{eachplate}/load_data_pipeline2.csv"

        with open(per_plate_csv, "rb") as a:
            s3.put_object(Body=a, Bucket=bucket, Key=csv_on_bucket_name)
        with open(per_plate_csv_2, "rb") as a:
            s3.put_object(Body=a, Bucket=bucket, Key=csv_on_bucket_name_2)

    # Now it's time to run DCP
    app_name = run_DCP.run_setup(bucket, prefix, batch, config_dict)

    # Make a batch
    if not SABER:
        pipeline_name = "1_CP_Illum.cppipe"
    if SABER:
        pipeline_name = "1_SABER_CP_Illum.cppipe"
    create_batch_jobs.create_batch_jobs_1(
        image_prefix, batch, pipeline_name, platelist, app_name
    )

    # Start a cluster
    run_DCP.run_cluster(bucket, prefix, batch, len(platelist), config_dict)

    # Run the monitor
    run_DCP.run_monitor(bucket, prefix, batch, step, config_dict)
    print("Go run the monitor now")

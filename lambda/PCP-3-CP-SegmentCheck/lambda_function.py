import datetime
import os, sys
import json
import boto3
import numpy
import pandas

sys.path.append("/opt/pooled-cell-painting-lambda")

import create_CSVs
import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Step information
metadata_file_name = "/tmp/metadata.json"
pipeline_name = "3_CP_SegmentationCheck.cppipe"
step = "3"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "2018_11_20_Periscope_X_PaintingSegmentationCheck",
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.1.3",
    "MACHINE_TYPE": "m4.xlarge",
    "MACHINE_PRICE": "0.10",
    "EBS_VOL_SIZE": "200",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "4",
    "MEMORY": "15000",
    "SECONDS_TO_START": "3 * 60",
    "SQS_MESSAGE_VISIBILITY": "20 * 60",
    "CHECK_IF_DONE_BOOL": "False",
    "EXPECTED_NUMBER_FILES": "5",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
}

# Default percentiles are 10 and 90. Change only to troubleshoot troublesome datasets.
upper_percentile = 90
lower_percentile = 10


def lambda_handler(event, context):
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    if "csv" in key:
        plate = key.split("/")[-2].split("-")[0]
        batch = key.split("/")[-5]
        image_prefix = key.split(batch)[0]

    else:
        batch = key.split("/")[-2]
        image_prefix = key.split("workspace")[0]

    prefix = os.path.join(image_prefix, "workspace/")
    print(batch, prefix)

    # get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print("Loading", metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(
        s3, bucket_name, metadata_file_name, metadata_on_bucket_name
    )

    image_dict = metadata["painting_file_data"]
    num_series = int(metadata["painting_rows"]) * int(metadata["painting_columns"])
    if metadata["painting_imperwell"] != "":
        if int(metadata["painting_imperwell"]) != 0:
            num_series = int(metadata["painting_imperwell"])
    out_range = list(range(0, num_series, int(metadata["range_skip"])))
    expected_files_per_well = (num_series * len(metadata["channel_list"])) + 6
    platelist = list(image_dict.keys())
    plate_and_well_list = []
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = list(platedict.keys())
        for eachwell in well_list:
            plate_and_well_list.append((eachplate, eachwell))
    metadata["painting_plate_and_well_list"] = plate_and_well_list
    helpful_functions.write_metadata_file(
        s3, bucket_name, metadata, metadata_file_name, metadata_on_bucket_name
    )

    # First let's check if it seems like the whole thing is done or not
    sqs = boto3.client("sqs")

    filter_prefix = image_prefix + batch + "/images_corrected/painting"
    # Expected length shows that all transfers (i.e. all wells) have at least started
    expected_len = ((len(plate_and_well_list) - 1) * expected_files_per_well) + 1

    print("Checking if all files are present")
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
        print("Checking CSVs for thresholds")
        image_csv_list = helpful_functions.paginate_a_folder(
            s3,
            bucket_name,
            os.path.join(image_prefix, batch, "images_corrected/painting"),
        )
        image_csv_list = [x for x in image_csv_list if "Image.csv" in x]
        image_df = helpful_functions.concat_some_csvs(
            s3, bucket_name, image_csv_list, "Image.csv"
        )
        threshes = image_df["Threshold_FinalThreshold_Cells"]
        calc_upper_percentile = numpy.percentile(threshes, upper_percentile)
        print(
            "In ",
            len(image_csv_list) * num_series,
            f"images, the {upper_percentile} percentile was",
            calc_upper_percentile,
        )
        calc_lower_percentile = numpy.percentile(threshes, lower_percentile)
        print(
            "In ",
            len(image_csv_list) * num_series,
            f"images, the {lower_percentile} percentile was",
            calc_lower_percentile,
        )

        pipeline_on_bucket_name = os.path.join(
            prefix, "pipelines", batch, pipeline_name
        )
        local_pipeline_name = os.path.join("/tmp", pipeline_name)
        local_temp_pipeline_name = os.path.join(
            "/tmp", pipeline_name.split(".")[0] + "_edited.cppipe"
        )
        with open(local_pipeline_name, "wb") as f:
            s3.download_fileobj(bucket_name, pipeline_on_bucket_name, f)
        edit_id_secondary(
            local_pipeline_name,
            local_temp_pipeline_name,
            calc_lower_percentile,
            calc_upper_percentile,
        )
        with open(local_temp_pipeline_name, "rb") as pipeline:
            s3.put_object(
                Body=pipeline, Bucket=bucket_name, Key=pipeline_on_bucket_name
            )
        print("Edited pipeline file")

        # Pull the file names we care about, and make the CSV
        for eachplate in platelist:
            platedict = image_dict[eachplate]
            well_list = list(platedict.keys())
            bucket_folder = (
                "/home/ubuntu/bucket/"
                + image_prefix
                + batch
                + "/images_corrected/painting"
            )
            per_plate_csv = create_CSVs.create_CSV_pipeline3(
                eachplate, num_series, bucket_folder, well_list, metadata["range_skip"]
            )
            csv_on_bucket_name = (
                prefix
                + "load_data_csv/"
                + batch
                + "/"
                + eachplate
                + "/load_data_pipeline3.csv"
            )
            print("Created", csv_on_bucket_name)
            with open(per_plate_csv, "rb") as a:
                s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)

        # now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name, prefix, batch, config_dict)

        # make the jobs
        create_batch_jobs.create_batch_jobs_3(
            image_prefix, batch, pipeline_name, plate_and_well_list, out_range, app_name
        )

        # Start a cluster
        run_DCP.run_cluster(
            bucket_name,
            prefix,
            batch,
            len(plate_and_well_list) * len(out_range),
            config_dict,
        )

        # Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch, step, config_dict)
        print("Go run the monitor now")
        return "Cluster started"


def edit_id_secondary(file_in_name, file_out_name, lower_value, upper_value):
    with open(file_in_name, "rt") as infile:
        with open(file_out_name, "wt") as outfile:
            IDSecond = False
            for line in infile:
                if "IdentifySecondaryObjects" in line:
                    IDSecond = True
                if "Lower and upper bounds on" in line and IDSecond == True:
                    prompt, answer = line.split(":")
                    new_answer = str(lower_value) + "," + str(upper_value)
                    line = prompt + ":" + new_answer + "\n"
                outfile.write(line)

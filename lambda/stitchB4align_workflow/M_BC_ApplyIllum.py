# EDIT LOAD DATA CSV WITH CORRECT CHANNEL PARSING

import json
import os
import sys
import time
import boto3

sys.path.append("/opt/pooled-cell-painting-lambda")

import create_CSVs
import run_DCP
import helpful_functions

s3 = boto3.client("s3")
sqs = boto3.client("sqs")

# Step information
metadata_file_name = "/tmp/metadata.json"
pipeline_name = "M_BC_ApplyIllum.cppipe"

# AWS Configuration Specific to this Function
config_dict = {
    "APP_NAME": "PROJECT_M_BC_ApplyIllum", # EDIT TO MATCH
    "DOCKERHUB_TAG": "cellprofiler/distributed-cellprofiler:2.0.0_4.2.4",
    "TASKS_PER_MACHINE": "1",
    "MACHINE_TYPE": ["m5.xlarge"], 
    "MACHINE_PRICE": "0.40",
    "EBS_VOL_SIZE": "40",
    "DOWNLOAD_FILES": "False",
    "DOCKER_CORES": "4",
    "MEMORY": "15000",
    "SECONDS_TO_START": "180",
    "SQS_MESSAGE_VISIBILITY": "43200",
    "CHECK_IF_DONE_BOOL": "False",
    "EXPECTED_NUMBER_FILES": "5",
    "MIN_FILE_SIZE_BYTES": "1",
    "NECESSARY_STRING": "",
} 

# List plates if you want to exclude them from run.
exclude_plates = []
# List plates if you want to only run them and exclude all others from run.
include_plates =[]

class JobQueue:
    def __init__(self, name=None):
        self.sqs = boto3.resource("sqs")
        self.queue = self.sqs.get_queue_by_name(QueueName=name)
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print(("Batch sent. Message ID:", response.get("MessageId")))


def lambda_handler(event, context):
    # Log the received event
    bucket_name = event["bucket_name"]
    batch = event["batch"]
    image_prefix = event["image_prefix"]
    prefix = os.path.join(image_prefix, "workspace/")
    app_name = config_dict["APP_NAME"]

    # Get the metadata file
    metadata_on_bucket_name = os.path.join(prefix, "metadata", batch, "metadata.json")
    print(f"Downloading metadata from {metadata_on_bucket_name}")
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
    # Create and write full plate_and_well_list
    plate_and_well_list = []
    for plate in platelist:
        platedict = image_dict[plate]
        for cycle in range(1, expected_cycles+1):
            cyclestr = str(cycle)
            well_list = list(platedict[cyclestr].keys())
            for well in well_list:
                plate_and_well_list.append((plate,well))
    metadata[
        "barcoding_plate_and_well_list"
    ] = plate_and_well_list = list(set(plate_and_well_list))
    helpful_functions.write_metadata_file(
        s3, bucket_name, metadata, metadata_file_name, metadata_on_bucket_name
    )
    # Apply filters to active plate_and_well_list
    if exclude_plates:
        platelist = [i for i in platelist if i not in exclude_plates]
        plate_and_well_list = [
            x for x in plate_and_well_list if x[0] not in exclude_plates
        ]
    if include_plates:
        platelist = include_plates
        plate_and_well_list = [x for x in plate_and_well_list if x[0] in include_plates]
    print (f"platelist {platelist}")
    print(f"plate_and_well_list {plate_and_well_list}")

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
        csv_on_bucket_name = f"{prefix}load_data_csv/{batch}/{eachplate}/load_data_M_BC_ApplyIllum.csv"
        print("Created", csv_on_bucket_name)
        with open(per_plate_csv, "rb") as a:
            s3.put_object(Body=a, Bucket=bucket_name, Key=csv_on_bucket_name)
    
    
    # now let's do our stuff!
    run_DCP.run_setup(bucket_name, prefix, batch, config_dict)
    

    # Submit jobs
    pipelinepath = os.path.join(image_prefix, "workspace","pipelines", batch)
    illumoutpath = os.path.join(image_prefix, batch, "images_illumcorrected","barcoding")
    datafilepath = os.path.join(image_prefix,"workspace","load_data_csv", batch)
    illumqueue = JobQueue(app_name + "Queue")
    for toillum in plate_and_well_list:
        for series in range(int(num_series)):
            templateMessage_illum = {
                "Metadata": "Metadata_Plate="
                + toillum[0]
                + ",Metadata_Well="
                + toillum[1]
                + ",Metadata_Site="
                + str(series),
                "pipeline": os.path.join(pipelinepath, pipeline_name),
                "output": illumoutpath,
                "output_structure": "Metadata_Plate-Metadata_Well",
                "input": pipelinepath,
                "data_file": os.path.join(
                    datafilepath, toillum[0], "load_data_M_BC_ApplyIllum.csv"
                ),
            }
            illumqueue.scheduleBatch(templateMessage_illum)
    print("Illum job submitted. Check your queue")
    
    
    # Start a cluster
    njobs = len(plate_and_well_list) * num_series
    run_DCP.run_cluster(bucket_name, prefix, batch, njobs, config_dict)
    
    # Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, "M_BC_ApplyIllum", config_dict)
    print("Go run the monitor now")
    return "Cluster started"
    
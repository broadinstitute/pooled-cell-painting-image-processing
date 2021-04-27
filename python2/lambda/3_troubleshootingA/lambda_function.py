from __future__ import print_function
import datetime
import os, sys
import json

import boto3
import numpy
import pandas

sys.path.append('/opt/pooled-cell-painting-lambda')

import create_CSVs
import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client('s3')
sqs = boto3.client('sqs')
pipeline_name = '3A_SegmentationCheckTroubleshooting_TI2.cppipe'
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'segmentFleet.json'
duplicate_queue_name = '2018_11_20_Periscope_PreventOverlappingStarts.fifo'
step = '3A'
config_step = '3' # Uses some configs from step 3
range_skip = 1

# Delete existing contents of images_segmentation folder before beginning

def lambda_handler(event, context):
    # Log the received event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    if 'csv' in key:
        plate = key.split('/')[-2].split('-')[0]
        batch = key.split('/')[-5]
        image_prefix = key.split(batch)[0]

    else:
        batch = key.split('/')[-2]
        image_prefix = key.split('workspace')[0]

    prefix = os.path.join(image_prefix,'workspace/')
    print(batch, prefix)

    # Get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix,'metadata',batch,'metadata.json')
    print('Loading', metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(s3, bucket_name, metadata_file_name, metadata_on_bucket_name)

    image_dict = metadata ['painting_file_data']
    num_series = int(metadata['painting_rows']) * int(metadata['painting_columns'])
    if "painting_imperwell" in metadata.keys():
        if metadata["painting_imperwell"] != "":
            if int(metadata["painting_imperwell"]) != 0:
                num_series = int(metadata["painting_imperwell"])
    out_range = range(0,num_series,range_skip)
    expected_files_per_well = (num_series*int(metadata['painting_channels']))+6
    platelist = image_dict.keys()
    plate_and_well_list = metadata['painting_plate_and_well_list']

    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = platedict.keys()
        bucket_folder = '/home/ubuntu/bucket/'+image_prefix+batch+'/images_corrected/painting'
        per_plate_csv = create_CSVs.create_CSV_pipeline3(eachplate, num_series, bucket_folder, well_list, range_skip)
        csv_on_bucket_name = prefix + 'load_data_csv/'+batch+'/'+eachplate+'/load_data_pipeline3A.csv'
        print('Created', csv_on_bucket_name)
        with open(per_plate_csv,'rb') as a:
            s3.put_object(Body= a, Bucket = bucket_name, Key = csv_on_bucket_name)

    # Now let's do our stuff!
    app_name = run_DCP.run_setup(bucket_name, prefix, batch, step)
    print('app_name is',app_name)

    # Make the jobs
    create_batch_jobs.create_batch_jobs_3A(image_prefix, batch, pipeline_name, platelist, well_list, app_name)

    # Start a cluster
    run_DCP.run_cluster(bucket_name, prefix, batch, config_step, fleet_file_name, len(platelist)*len(well_list))

    # Create the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch, step)
    print('Go run the monitor now')
    return('Cluster started')

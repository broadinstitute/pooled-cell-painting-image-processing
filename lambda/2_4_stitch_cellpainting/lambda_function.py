from __future__ import print_function

import json
import os
import sys
import time

import boto3

sys.path.append('/opt/pooled-cell-painting-lambda')

import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client('s3')
sqs = boto3.client('sqs')
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'stitchFleet.json'
prev_step_app_name = '2018_11_20_Periscope_X_ApplyIllumPainting'
prev_step_num = '2'
step = '4'

def lambda_handler(event, context):
    # Log the received event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    keys = [x['s3']['object']['key'] for x in event['Records'] ]
    plate = key.split('/')[-2].split('-')[0]
    batch = key.split('/')[-5]
    image_prefix = key.split(batch)[0]
    prefix = os.path.join(image_prefix,'workspace/')
    
    print(plate,batch,image_prefix,prefix)
    
    #get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix,'metadata',batch,'metadata.json')
    print('Loading', metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(s3, bucket_name, metadata_file_name, metadata_on_bucket_name)
    
    image_dict = metadata ['painting_file_data']
    print(image_dict)
    num_series = int(metadata['painting_rows']) * int(metadata['painting_columns'])
    expected_files_per_well = (num_series*int(metadata['painting_channels']))+6
    platelist = image_dict.keys()
    plate_and_well_list = []
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = platedict.keys()
        for eachwell in well_list:
            plate_and_well_list.append((eachplate,eachwell))
    metadata['painting_plate_and_well_list'] = plate_and_well_list
    helpful_functions.write_metadata_file(s3, bucket_name, metadata, metadata_file_name, metadata_on_bucket_name)

    #First let's check if it seems like the whole thing is done or not
    sqs = boto3.client('sqs')
    
    filter_prefix = image_prefix+batch+'/images_corrected/painting'
    expected_len = len(plate_and_well_list) * expected_files_per_well
    
    done = helpful_functions.check_if_run_done(s3, bucket_name, filter_prefix, expected_len, prev_step_app_name, sqs)
    
    if not done:
        print('Still work ongoing')
    else:
        # first let's just try to run the monitor on the last step, in case we haven't yet
        helpful_functions.try_a_shutdown(s3, bucket_name, prefix, batch, prev_step_num, prev_step_app_name)
        
        #now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name,prefix,batch,step,cellprofiler = False)
        
        #make the jobs
        create_batch_jobs.create_batch_jobs_4(image_prefix,batch,metadata,plate_and_well_list, app_name)
        
        #Start a cluster
        run_DCP.run_cluster(bucket_name,prefix,batch,step, fleet_file_name, len(plate_and_well_list))  

        #Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch,step)
        print('Go run the monitor now')
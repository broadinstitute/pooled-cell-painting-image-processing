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
pipeline_name_list = ['6A_Apply_Illum_forBarcoding_TI2_NormCC.cppipe','6B_Apply_Illum_forBarcoding_TI2_AlignToA.cppipe', '6C_Apply_Illum_forBarcoding_TI2_SqRt.cppipe']
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'illumFleet.json'
step = '6A'

def lambda_handler(event, context):
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    keys = [x['s3']['object']['key'] for x in event['Records'] ]
    batch = key.split('/')[-2]
    image_prefix = key.split('workspace')[0]
    prefix = os.path.join(image_prefix,'workspace/')
    
    print(batch,image_prefix,prefix)
    
    #get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix,'metadata',batch,'metadata.json')
    print('Loading', metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(s3, bucket_name, metadata_file_name, metadata_on_bucket_name)
    plate_and_well_list = metadata['barcoding_plate_and_well_list']
    
    #First let's check if it seems like the whole thing is done or not
    sqs = boto3.client('sqs')
    
    #now let's do our stuff!
    app_name = run_DCP.run_setup(bucket_name,prefix,batch,step)
        
    #make the jobs
    #create_batch_jobs.create_batch_jobs_6A(image_prefix,batch,pipeline_name_list,plate_and_well_list, app_name)
        
    #Start a cluster
    run_DCP.run_cluster(bucket_name,prefix,batch,step, fleet_file_name, len(plate_and_well_list)*len(pipeline_name_list))  

    #Run the monitor
    #run_DCP.run_monitor(bucket_name, prefix, batch,step)
    print('Go run the monitor now')
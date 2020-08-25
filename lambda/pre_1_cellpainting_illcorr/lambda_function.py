from __future__ import print_function

import json
import os
import sys

import boto3

sys.path.append('/opt/pooled-cell-painting-lambda')

import create_CSVs
import run_DCP
import create_batch_jobs
import helpful_functions

print('Loading function')

s3 = boto3.client('s3')
pipeline_name = '1_Illum_forCP_TI2.cppipe'
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'illumFleet.json'
step = '1'

def lambda_handler(event, context):
    # Log the received event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    prefix, batchAndPipe = key.split('pipelines/')
    image_prefix = prefix.split('workspace')[0]
    batch = batchAndPipe.split(pipeline_name)[0][:-1]

    #get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix,'metadata',batch,'metadata.json')
    metadata = helpful_functions.download_and_read_metadata_file(s3, bucket, metadata_file_name, metadata_on_bucket_name)
    num_series = int(metadata['painting_rows']) * int(metadata['painting_columns'])
    if "painting_imperwell" in metadata.keys():
        if metadata["painting_imperwell"] != "":
            if int(metadata["painting_imperwell"]) != 0:
                num_series = int(metadata["painting_imperwell"])
    
    
    #Get the list of images in this experiment
    image_list_prefix = image_prefix+batch+'/images/'
    image_list = helpful_functions.paginate_a_folder(s3,bucket,image_list_prefix)
    image_dict = helpful_functions.parse_image_names(image_list,filter='20X')
    metadata ['painting_file_data'] = image_dict
    helpful_functions.write_metadata_file(s3, bucket, metadata, metadata_file_name, metadata_on_bucket_name)

    if metadata['one_or_many_files'] == 'one':
        full_well_files = 1
    else:
        full_well_files = num_series
    
    #Pull the file names we care about, and make the CSV
    platelist = image_dict.keys()
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = platedict.keys()
        paint_cycle_name = platedict[well_list[0]].keys()[0]
        per_well_im_list = []
        for eachwell in well_list:
            per_well = platedict[eachwell][paint_cycle_name]
            per_well.sort()
            if len(per_well)==full_well_files:
                per_well_im_list.append(per_well)
        bucket_folder = '/home/ubuntu/bucket/'+image_prefix+batch+'/images/'+eachplate+'/'+paint_cycle_name
        per_plate_csv = create_CSVs.create_CSV_pipeline1(eachplate, num_series, bucket_folder, per_well_im_list, metadata['one_or_many_files'])
        csv_on_bucket_name = prefix + 'load_data_csv/'+batch+'/'+eachplate+'/load_data_pipeline1.csv'
        with open(per_plate_csv,'rb') as a:
            s3.put_object(Body= a, Bucket = bucket, Key = csv_on_bucket_name )
            
    #Now it's time to run DCP
    #Replacement for 'fab setup'
    app_name = run_DCP.run_setup(bucket,prefix,batch,step)
    #run_DCP.grab_batch_config(bucket,prefix,batch,step)
    
    #Make a batch
    create_batch_jobs.create_batch_jobs_1(image_prefix,batch,pipeline_name,platelist, app_name)
    
    #Start a cluster
    run_DCP.run_cluster(bucket,prefix,batch,step, fleet_file_name, len(platelist))  

    #Run the monitor
    run_DCP.run_monitor(bucket, prefix, batch,step)
    print('Go run the monitor now')
    


            
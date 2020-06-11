from __future__ import print_function

import json
import os
import sys
import time

import boto3

sys.path.append('/opt/pooled-cell-painting-lambda')

import create_CSVs
import run_DCP
import create_batch_jobs
import helpful_functions

s3 = boto3.client('s3')
sqs = boto3.client('sqs')
pipeline_name = '7_Barcoding_Preprocessing.cppipe'
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'preprocessFleet.json'
prev_step_app_name = '2018_11_20_Periscope_Calico_ApplyIllumBarcoding'
prev_step_num = '6'
step = '7'

def lambda_handler(event, context):
    # Log the received event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    keys = [x['s3']['object']['key'] for x in event['Records'] ]
    plate = key.split('/')[-2].split('_')[0]
    batch = key.split('/')[-5]
    image_prefix = key.split(batch)[0]
    prefix = os.path.join(image_prefix,'workspace/')
    
    print(plate,batch,image_prefix,prefix)
    
    #get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix,'metadata',batch,'metadata.json')
    print('Loading', metadata_on_bucket_name)
    metadata = helpful_functions.download_and_read_metadata_file(s3, bucket_name, metadata_file_name, metadata_on_bucket_name)
    
    plate_and_well_list = metadata['barcoding_plate_and_well_list']
    image_dict = metadata['wells_with_all_cycles']
    expected_cycles = metadata['barcoding_cycles']
    platelist = image_dict.keys()
    num_series = int(metadata['barcoding_rows']) * int(metadata['barcoding_columns'])
    expected_files_per_well = (num_series*((int(metadata['barcoding_cycles'])*4)+1))+3
    num_sites = len(plate_and_well_list) * num_series
    
    #First let's check if it seems like the whole thing is done or not
    sqs = boto3.client('sqs')
    
    filter_prefix = image_prefix+batch+'/images_aligned/barcoding'
    expected_len = len(plate_and_well_list) * expected_files_per_well

    
    done = helpful_functions.check_if_run_done(s3, bucket_name, filter_prefix, expected_len, prev_step_app_name, sqs)
    
    if not done:
        print('Still work ongoing')
    else:
        #Pull the file names we care about, and make the CSV
        for eachplate in platelist:
            platedict = image_dict[eachplate]
            well_list = platedict['1'].keys()
            bucket_folder = '/home/ubuntu/bucket/'+image_prefix+batch+'/images_aligned/barcoding'
            per_plate_csv = create_CSVs.create_CSV_pipeline7(eachplate, num_series, expected_cycles, bucket_folder, well_list)
            csv_on_bucket_name = prefix + 'load_data_csv/'+batch+'/'+eachplate+'/load_data_pipeline7.csv'
            print('Created', csv_on_bucket_name)
            with open(per_plate_csv,'rb') as a:
                s3.put_object(Body= a, Bucket = bucket_name, Key = csv_on_bucket_name)
                
        # first let's just try to run the monitor on the last step, in case we haven't yet
        helpful_functions.try_a_shutdown(s3, bucket_name, prefix, batch, prev_step_num, prev_step_app_name)
        
        #now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name,prefix,batch,step)
        
        #make the jobs
        create_batch_jobs.create_batch_jobs_7(image_prefix,batch,pipeline_name,plate_and_well_list, range(num_series), app_name)
        
        #Start a cluster
        run_DCP.run_cluster(bucket_name,prefix,batch,step, fleet_file_name, num_sites)  

        #Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch,step)
        print('Go run the monitor now')
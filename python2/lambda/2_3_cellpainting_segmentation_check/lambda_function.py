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
pipeline_name = '3_SegmentationCheck_TI2.cppipe'
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'segmentFleet.json'
current_app_name = '2018_11_20_Periscope_X_PaintingSegmentationCheck'
prev_step_app_name = '2018_11_20_Periscope_X_ApplyIllumPainting'
duplicate_queue_name = '2018_11_20_Periscope_PreventOverlappingStarts.fifo'
step = '3'
#If you change range_skip, you must also change it in 3_4_stitch_cellpainting lambda function
range_skip = 16

def lambda_handler(event, context):
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

    #get the metadata file, so we can add stuff to it
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

    #First let's check if it seems like the whole thing is done or not
    sqs = boto3.client('sqs')

    filter_prefix = image_prefix+batch+'/images_corrected/painting'
    #Expected length shows that all transfers (i.e. all wells) have at least started
    expected_len = ((len(plate_and_well_list) - 1 )* expected_files_per_well) + 1

    print('Checking if all files are present')
    done = helpful_functions.check_if_run_done(s3, bucket_name, filter_prefix, expected_len, current_app_name, prev_step_app_name, sqs, duplicate_queue_name)

    if not done:
        print('Still work ongoing')
        return('Still work ongoing')
    else:
        print("Checking CSVs for what the upper threshold should be")
        image_csv_list = helpful_functions.paginate_a_folder(s3, bucket_name, os.path.join(image_prefix,batch,'images_corrected/painting'))
        image_csv_list = [x for x in image_csv_list if 'Image.csv' in x]
        image_df = helpful_functions.concat_some_csvs(s3, bucket_name,image_csv_list, 'Image.csv')
        threshes = image_df['Threshold_FinalThreshold_Cells']
        percentile = numpy.percentile(threshes,90)
        print("In ",len(image_csv_list)*num_series,"images, the 90th percentile was",percentile)

        pipeline_on_bucket_name = os.path.join(prefix,'pipelines',batch,pipeline_name)
        local_pipeline_name = os.path.join('/tmp',pipeline_name)
        local_temp_pipeline_name = os.path.join('/tmp',pipeline_name.split('.')[0]+'_edited.cppipe')
        with open(local_pipeline_name, 'wb') as f:
            s3.download_fileobj(bucket_name,  pipeline_on_bucket_name, f)
        edit_id_secondary(local_pipeline_name,local_temp_pipeline_name,percentile)
        with open(local_temp_pipeline_name, 'rb') as pipeline:
            s3.put_object(Body = pipeline, Bucket = bucket_name, Key = pipeline_on_bucket_name)
        print('Edited pipeline file')

        #Pull the file names we care about, and make the CSV
        for eachplate in platelist:
            platedict = image_dict[eachplate]
            well_list = platedict.keys()
            bucket_folder = '/home/ubuntu/bucket/'+image_prefix+batch+'/images_corrected/painting'
            per_plate_csv = create_CSVs.create_CSV_pipeline3(eachplate, num_series, bucket_folder, well_list, range_skip)
            csv_on_bucket_name = prefix + 'load_data_csv/'+batch+'/'+eachplate+'/load_data_pipeline3.csv'
            print('Created', csv_on_bucket_name)
            with open(per_plate_csv,'rb') as a:
                s3.put_object(Body= a, Bucket = bucket_name, Key = csv_on_bucket_name)

        #now let's do our stuff!
        app_name = run_DCP.run_setup(bucket_name,prefix,batch,step)

        #make the jobs
        create_batch_jobs.create_batch_jobs_3(image_prefix,batch,pipeline_name,plate_and_well_list, out_range, app_name)

        #Start a cluster
        run_DCP.run_cluster(bucket_name,prefix,batch,step, fleet_file_name, len(plate_and_well_list)*len(out_range))

        #Run the monitor
        run_DCP.run_monitor(bucket_name, prefix, batch,step)
        print('Go run the monitor now')
        return('Cluster started')


def edit_id_secondary(file_in_name,file_out_name,upper_value):
    with open(file_in_name,'rb') as infile:
        with open(file_out_name,'wb') as outfile:
            IDSecond = False
            for line in infile:
                if 'IdentifySecondaryObjects' in line:
                    IDSecond = True
                if 'Lower and upper bounds on' in line and IDSecond == True:
                    prompt,answer = line.split(':')
                    decoded_answer = answer.decode('string_escape')[:-1].decode('utf-16')
                    decoded_answer = decoded_answer[:decoded_answer.index(',')+1]+str(upper_value)
                    line = prompt+':'+decoded_answer.encode('utf16').encode('string_escape')+"\n"
                outfile.write(line)

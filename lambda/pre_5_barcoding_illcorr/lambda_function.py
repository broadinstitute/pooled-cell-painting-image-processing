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
pipeline_name = '5_Illum_forBarcoding_TI2.cppipe'
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = 'illumFleet.json'
step = '5'

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
    num_series = int(metadata['barcoding_rows']) * int(metadata['barcoding_columns'])
    if "barcoding_imperwell" in metadata.keys():
        if metadata["barcoding_imperwell"] != "":
            if int(metadata["barcoding_imperwell"]) != 0:
                num_series = int(metadata["barcoding_imperwell"])
    expected_cycles = int(metadata['barcoding_cycles'])

    #Get the list of images in this experiment - this can take a long time for big experiments so let's add some prints
    print('Getting the list of images')
    image_list_prefix = image_prefix+batch+'/images/' #the slash here is critical, because we don't want to read images_corrected because it's huge
    image_list = helpful_functions.paginate_a_folder(s3,bucket,image_list_prefix)
    print('Image list retrieved')
    image_dict = helpful_functions.parse_image_names(image_list,filter='10X')
    metadata ['barcoding_file_data'] = image_dict
    print('Parsing the image list')
    #We've saved the previous for looking at/debugging later, but really all we want is the ones with all cycles
    if metadata['one_or_many_files'] == 1:
        parsed_image_dict = helpful_functions.return_full_wells(image_dict,expected_cycles, metadata['one_or_many_files'])
    else:
        parsed_image_dict = helpful_functions.return_full_wells(image_dict,expected_cycles, metadata['one_or_many_files'], files_per_well=num_series)
    metadata['wells_with_all_cycles'] = parsed_image_dict
    helpful_functions.write_metadata_file(s3, bucket, metadata, metadata_file_name, metadata_on_bucket_name)

    #Pull the file names we care about, and make the CSV
    print('Making the CSVs')
    platelist = image_dict.keys()
    for eachplate in platelist:
        platedict = parsed_image_dict[eachplate]
        well_list = platedict.keys()
        bucket_folder = '/home/ubuntu/bucket/'+image_prefix+batch+'/images/'+eachplate
        per_plate_csv = create_CSVs.create_CSV_pipeline5(eachplate, num_series, expected_cycles, bucket_folder, platedict, metadata['one_or_many_files'], metadata["fast_or_slow_mode"])
        csv_on_bucket_name = prefix + 'load_data_csv/'+batch+'/'+eachplate+'/load_data_pipeline5.csv'
        with open(per_plate_csv,'rb') as a:
            s3.put_object(Body= a, Bucket = bucket, Key = csv_on_bucket_name )

    #Now it's time to run DCP
    #Replacement for 'fab setup'
    app_name = run_DCP.run_setup(bucket,prefix,batch,step)
    #run_DCP.grab_batch_config(bucket,prefix,batch,step)

    #Make a batch
    create_batch_jobs.create_batch_jobs_5(image_prefix,batch,pipeline_name,platelist, expected_cycles, app_name)

    #Start a cluster
    run_DCP.run_cluster(bucket,prefix,batch,step, fleet_file_name, len(platelist)*expected_cycles)

    #Run the monitor
    run_DCP.run_monitor(bucket, prefix, batch,step)
    print('Go run the monitor now')

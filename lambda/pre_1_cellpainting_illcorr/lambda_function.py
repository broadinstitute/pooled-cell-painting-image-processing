from __future__ import print_function

import json
import os

import boto3

import create_CSVs
import run_DCP
import create_batch_jobs

print('Loading function')

s3 = boto3.client('s3')
pipeline_name = '1_Illum_forCP_TI2.cppipe'
metadata_file_name = '/tmp/metadata.json'
fleet_file_name = '/tmp/fleet_file_1.json'

def lambda_handler(event, context):
    # Log the received event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    prefix, batchAndPipe = key.split('pipelines/')
    image_prefix = prefix.split('workspace')[0]
    batch = batchAndPipe.split(pipeline_name)[0][:-1]

    #get the metadata file, so we can add stuff to it
    metadata_on_bucket_name = os.path.join(prefix,'metadata',batch,'metadata.json')
    with open(metadata_file_name, 'wb') as f:
        s3.download_fileobj(bucket_name,  metadata_on_bucket_name, f)
    with open(metadata_file_name, 'r') as input_metadata:
        metadata = json.load(input_metadata)
    num_series = int(metadata['painting_rows']) * int(metadata['painting_columns'])
    #Get the list of images in this experiment
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=image_prefix+batch+'/images')
    image_list = []
    #image_list = s3.list_objects_v2(Bucket=bucket_name,Prefix=)['Contents']
    for page in pages:
        image_list += [x['Key'] for x in page['Contents']]
    image_dict = parse_image_names(image_list,filter='20X')
    metadata ['painting_file_data'] = image_dict
    with open(metadata_file_name, 'wb') as f:
        json.dump(metadata, f)
    with open(metadata_file_name, 'r') as metadata:
        s3.put_object(Body = metadata, Bucket = bucket_name, Key = metadata_on_bucket_name)
    
    #Pull the file names we care about, and make the CSV
    platelist = image_dict.keys()
    for eachplate in platelist:
        platedict = image_dict[eachplate]
        well_list = platedict.keys()
        paint_cycle_name = platedict[well_list[0]].keys()[0]
        per_well_im_list = []
        for eachwell in well_list:
            per_well = platedict[eachwell][paint_cycle_name]
            per_well.sort(reverse=True)
            if len(per_well)==3:
                per_well = [per_well[0],per_well[2]] #we don't want the slow phalloidin for this
                per_well_im_list.append(per_well)
        bucket_folder = '/home/ubuntu/bucket/'+image_prefix+batch+'/images/'+eachplate+'/'+paint_cycle_name
        per_plate_csv = create_CSVs.create_CSV_pipeline1(eachplate, num_series, bucket_folder, per_well_im_list)
        csv_on_bucket_name = prefix + 'load_data_csv/'+batch+'/'+eachplate+'/load_data_pipeline1.csv'
        with open(per_plate_csv,'rb') as a:
            s3.put_object(Body= a, Bucket = bucket_name, Key = csv_on_bucket_name )
            
    #Now it's time to run DCP
    #Replacement for 'fab setup'
    run_DCP.run_setup(bucket_name,prefix,batch,'1')
    #run_DCP.grab_batch_config(bucket_name,prefix,batch,'1')
    
    #Make a batch
    create_batch_jobs.create_batch_jobs_1(image_prefix,batch,pipeline_name,platelist)
    
    #Start a cluster
    run_DCP.run_cluster(bucket_name,prefix,batch,'1', 'illumFleet.json', len(platelist))  

    #Run the monitor
    run_DCP.run_monitor(bucket_name, prefix, batch,'1')
    print('Go run the monitor now')
    
def parse_image_names(imlist,filter):
    image_dict = {}
    for image in imlist:
        if '.nd2' in image:
            if filter in image:
                prePlate,platePlus = image.split('images/')
                plate,cycle,imname = platePlus.split('/')
                well = imname[:imname.index('_')]
                if plate not in image_dict.keys():
                    image_dict[plate] = {well:{cycle:[imname]}}
                else:
                    if well not in image_dict[plate].keys():
                        image_dict[plate][well] = {cycle:[imname]}
                    else:
                        if cycle not in image_dict[plate][well].keys():
                            image_dict[plate][well][cycle] = [imname]
                        else:
                            image_dict[plate][well][cycle] += [imname]
    return image_dict

            
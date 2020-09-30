import json
import os
import re
import sys
import time

import pandas

import run_DCP

def parse_image_names(imlist,filter_in, filter_out="jibberish"):
    image_dict = {}
    for image in imlist:
        if '.nd2' in image:
            if filter_in.lower() in image.lower():
                if filter_out.lower() not in image.lower():
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

def return_full_wells(image_dict,expected_cycles,one_or_many, files_per_well=1):
    im_dict_out = {}
    expected_cycles = int(expected_cycles)
    platelist = image_dict.keys()
    for eachplate in platelist:
        print('Checking compeleteness of plate', eachplate)
        platedict = image_dict[eachplate]
        well_list = platedict.keys()
        #first let's see how many wells have every cycle
        full_wells = []
        for eachwell in well_list:
            cycle_list = platedict[eachwell].keys()
            if len(cycle_list) == expected_cycles:
                has_all_files = True
                #let's also make sure each cycle has all its files; for Cycle 1, that's 1, for the rest it's 5
                for cycle in cycle_list:
                    if len(platedict[eachwell][cycle]) not in (files_per_well,files_per_well*5):
                        has_all_files = False
                        print ("Plate", eachplate, "Well", eachwell, "Cycle", cycle, "only had", len(platedict[eachwell][cycle]), "files")
                if has_all_files:
                    full_wells.append(eachwell)

        #Initialize our output dictionary for the plate
        print('Writing out the output for plate',eachplate,'has full wells',full_wells)
        per_cycle_dict={}
        for cycle in range(1,expected_cycles+1):
            per_cycle_dict[cycle]={}
        for eachwell in full_wells:
            cycle_list = platedict[eachwell].keys()
            for cycle in cycle_list:
                match = re.search('[-_]c[_-]{0,1}[0-9]{1,2}',cycle)
                out = match.group(0)
                cycle_num = int(out[out.index('c')+1:])
                if cycle_num == 1 and one_or_many =='one':
                    per_cycle_dict[cycle_num][eachwell]=[cycle,platedict[eachwell][cycle]*5]
                else:
                    temp_list = platedict[eachwell][cycle]
                    temp_list.sort()
                    per_cycle_dict[cycle_num][eachwell]=[cycle,temp_list]
        im_dict_out[eachplate] = per_cycle_dict
    return im_dict_out

def download_and_read_metadata_file(s3, bucket_name, metadata_file_name, metadata_on_bucket_name):
    with open(metadata_file_name, 'wb') as f:
        s3.download_fileobj(bucket_name,  metadata_on_bucket_name, f)
    with open(metadata_file_name, 'r') as input_metadata:
        metadata = json.load(input_metadata)
    return metadata

def write_metadata_file(s3, bucket_name, metadata, metadata_file_name, metadata_on_bucket_name):
    with open(metadata_file_name, 'wb') as f:
        json.dump(metadata, f)
    with open(metadata_file_name, 'r') as metadata:
        s3.put_object(Body = metadata, Bucket = bucket_name, Key = metadata_on_bucket_name)

def paginate_a_folder(s3,bucket_name,prefix):
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    image_list = []
    #image_list = s3.list_objects_v2(Bucket=bucket_name,Prefix=)['Contents']
    for page in pages:
        image_list += [x['Key'] for x in page['Contents']]
    return image_list

def check_if_run_done(s3, bucket_name, filter_prefix, expected_len, current_app_name, prev_step_app_name, sqs, dup_queue_name, filter_in = None, filter_out = None):
    #Step 1- how many files are there in the illum folder?
    image_list = paginate_a_folder(s3, bucket_name, filter_prefix)
    done = False

    if filter_in != None:
        image_list = [x for x in image_list if filter_in in x]
    if filter_out != None:
        image_list = [x for x in image_list if filter_out not in x]

    if len(image_list) >= expected_len:
        done = True
    else:
        print('Only ',len(image_list),' output files so far')

    #Maybe something died, but everything is done, and you have a monitor on that already cleaned up your queue
    queue_url = check_named_queue(sqs, prev_step_app_name+'Queue')
    if queue_url == None:
        done = True

    else:
        #Maybe something died, and now your queue is just at 0 jobs
        attributes = sqs.get_queue_attributes(QueueUrl=queue_url,AttributeNames=['ApproximateNumberOfMessages','ApproximateNumberOfMessagesNotVisible'])
        if attributes['Attributes']['ApproximateNumberOfMessages'] + attributes['Attributes']['ApproximateNumberOfMessagesNotVisible'] == 0:
            done = True

    #If indeed we are done, we want to check we're not overlapping and starting the same next job many times
    if done:
        # Check if current queue exists already (job already triggered)
        current_queue_url = check_named_queue(sqs, current_app_name+'Queue')
        if current_queue_url != None:
            return False
        # Check FIFO queue
        dup_queue_url=check_named_queue(sqs, dup_queue_name)
        nmess = sqs.get_queue_attributes(QueueUrl=dup_queue_url,AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages']
        sqs.send_message(QueueUrl=dup_queue_url, MessageBody=prev_step_app_name, MessageGroupId='0')
        time.sleep(2)
        nmess2 = sqs.get_queue_attributes(QueueUrl=dup_queue_url,AttributeNames=['ApproximateNumberOfMessages'])['Attributes']['ApproximateNumberOfMessages']
        if nmess2 != nmess: #aka, if we're the first job to report in as finished
            return True

    #or, we're just not done yet
    return False

def check_named_queue(sqs, SQS_QUEUE_NAME):
    result = sqs.list_queues()
    if 'QueueUrls' in result.keys():
        for u in result['QueueUrls']:
            if u.split('/')[-1] == SQS_QUEUE_NAME:
                return u
    return None

def try_to_run_monitor(s3, bucket_name, prefix, batch, step, prev_step_app_name):
    prev_step_monitor_bucket_name = prefix + 'monitors/'+batch+'/'+step+'/'+prev_step_app_name + 'SpotFleetRequestId.json'
    prev_step_monitor_name = '/tmp/'+prev_step_app_name + 'SpotFleetRequestId.json'
    print('Trying to shut down ',prev_step_monitor_bucket_name)
    with open(prev_step_monitor_name, 'wb') as f:
        s3.download_fileobj(bucket_name,  prev_step_monitor_bucket_name, f)
    print('Grabbing config for batch',batch,'step',step)
    run_DCP.grab_batch_config(bucket_name,prefix,batch,step)
    import boto3_setup
    boto3_setup.monitor()

def try_a_shutdown(s3, bucket_name, prefix, batch, prev_step_number, prev_step_app_name):
    print('Trying monitor')
    try:
        import botocore
        try_to_run_monitor(s3, bucket_name, prefix, batch, str(prev_step_number), prev_step_app_name)
    except botocore.exceptions.ClientError as error:
        print('Monitor cleanup of previous step failed with error: ',error)
        print('Usually this is no existing queue by that name, maybe a previous monitor cleaned up')
    except:
        print('Monitor cleanup of previous step failed with error',sys.exc_info()[0])
        pass

def concat_some_csvs(s3,bucket_name,file_list,csvname):
    tmp_name = os.path.join('/tmp',csvname)
    df_dict={}
    count = 0
    for eachfile in file_list:
        with open(tmp_name, 'wb') as f:
            s3.download_fileobj(bucket_name,  eachfile, f)
        df_dict[eachfile]=pandas.read_csv(tmp_name,index_col=False)
        count+=1
        if count % 100 == 0:
            print(count)
    df_merged = pandas.concat(df_dict, ignore_index=True)
    return df_merged

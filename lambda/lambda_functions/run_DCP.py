
import os
import sys

import boto3

sys.path.append('/tmp')

def run_setup(bucket_name,prefix,batch,step):
    os.chdir('/tmp')
    grab_batch_config(bucket_name,prefix,batch,step)
    import boto3_setup
    boto3_setup.setup()
    
def run_cluster(bucket_name,prefix,batch,step, filename, njobs):
    os.chdir('/tmp')
    grab_fleet_file(bucket_name,prefix,batch,step, filename)
    import boto3_setup
    boto3_setup.startCluster('fleet_ours.json', njobs)

def run_monitor(bucket_name, prefix, batch,step):
    import boto3_setup
    boto3_setup.upload_monitor(bucket_name, prefix, batch,step)

def grab_batch_config(bucket_name,prefix,batch,step):
    s3 = boto3.client('s3')
    our_config = prefix+'lambda/'+batch+'/'+str(step)+'/config_ours_full.py'
    with open('/tmp/config_ours.py', 'wb') as f:
        s3.download_fileobj(bucket_name, our_config, f)

def grab_fleet_file(bucket_name,prefix,batch,step, filename):
    s3 = boto3.client('s3')
    our_fleet = prefix+'lambda/'+batch+'/'+str(step)+'/' + filename
    with open('/tmp/fleet_ours.json', 'wb') as f:
        s3.download_fileobj(bucket_name, our_fleet, f)        
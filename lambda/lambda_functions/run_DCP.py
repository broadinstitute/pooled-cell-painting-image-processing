import os
import sys
import boto3

sys.path.append("/tmp")

def run_setup(bucket_name, prefix, batch, step, cellprofiler=True):
    os.chdir("/tmp")
    if os.path.exists("/tmp/config_ours.py"):
        os.remove("/tmp/config_ours.py")
        print("removed previous config file")
    grab_batch_config(bucket_name, prefix, batch, step)
    # We might sometimes run setup after running cleanup on the step before, so we want to import our configs fresh
    if "boto3_setup" in list(sys.modules.keys()):
        sys.modules.pop("boto3_setup")
        print("popped previous boto3_setup")
    if "config_ours" in list(sys.modules.keys()):
        sys.modules.pop("config_ours")
        print("popped previous config_ours")
    import boto3_setup
    app_name = boto3_setup.setup(cellprofiler=cellprofiler)
    return app_name

def run_cluster(bucket_name, prefix, batch, step, filename, njobs):
    os.chdir("/tmp")
    grab_fleet_file(bucket_name, prefix, batch, step, filename)
    import boto3_setup
    boto3_setup.startCluster("fleet_ours.json", njobs)

def run_monitor(bucket_name, prefix, batch, step):
    import boto3_setup
    boto3_setup.upload_monitor(bucket_name, prefix, batch, step)

def grab_batch_config(bucket_name, prefix, batch, step):
    s3 = boto3.client("s3")
    our_config = prefix + "lambda/" + batch + "/" + str(step) + "/config_ours.py"
    import botocore
    try:
        with open("/tmp/config_ours.py", "wb") as f:
            s3.download_fileobj(bucket_name, our_config, f)
    except botocore.exceptions.ClientError as error:
        print ("Config files for this batch haven't been uploaded to S3.")
        return

def grab_fleet_file(bucket_name, prefix, batch, step, filename):
    s3 = boto3.client("s3")
    our_fleet = prefix + "lambda/" + batch + "/" + str(step) + "/" + filename
    try:
        with open("/tmp/fleet_ours.json", "wb") as f:
            s3.download_fileobj(bucket_name, our_fleet, f)
    except botocore.exceptions.ClientError as error:
        print ("Error grabbing fleet file.")
        return

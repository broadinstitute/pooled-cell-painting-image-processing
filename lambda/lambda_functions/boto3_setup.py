import os, sys
import boto3
import datetime
import json
import time
from base64 import b64encode

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import numpy

CPU_SHARES = 1024
from configAWS import *

WAIT_TIME = 60
MONITOR_TIME = 60

#################################
# AUXILIARY FUNCTIONS
#################################


def generate_task_definition(config_dict):
    task_definition = {
        "family": config_dict["APP_NAME"],
        "containerDefinitions": [
            {
                "environment": [{"name": "AWS_REGION", "value": AWS_REGION}],
                "name": config_dict["APP_NAME"],
                "image": config_dict["DOCKERHUB_TAG"],
                "cpu": CPU_SHARES,
                "memory": config_dict["MEMORY"],
                "essential": True,
                "privileged": True,
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": LOG_GROUP_NAME + "_perInstance",
                        "awslogs-region": AWS_REGION,
                        "awslogs-stream-prefix": config_dict["APP_NAME"],
                    },
                },
            }
        ],
    }
    sqs = boto3.client("sqs")
    queue_name = get_queue_url(sqs)
    task_definition["containerDefinitions"][0]["environment"] += [
        {"name": "APP_NAME", "value": config_dict["APP_NAME"]},
        {"name": "SQS_QUEUE_URL", "value": queue_name},
        {"name": "AWS_ACCESS_KEY_ID", "value": os.environ["MY_AWS_ACCESS_KEY_ID"]},
        {
            "name": "AWS_SECRET_ACCESS_KEY",
            "value": os.environ["MY_AWS_SECRET_ACCESS_KEY"],
        },
        {"name": "AWS_BUCKET", "value": AWS_BUCKET},
        {"name": "DOCKER_CORES", "value": str(config_dict["DOCKER_CORES"])},
        {"name": "LOG_GROUP_NAME", "value": LOG_GROUP_NAME},
        {"name": "CHECK_IF_DONE_BOOL", "value": config_dict["CHECK_IF_DONE_BOOL"]},
        {
            "name": "EXPECTED_NUMBER_FILES",
            "value": str(config_dict["EXPECTED_NUMBER_FILES"]),
        },
        {"name": "ECS_CLUSTER", "value": ECS_CLUSTER},
        {"name": "SECONDS_TO_START", "value": str(config_dict["SECONDS_TO_START"])},
        {
            "name": "MIN_FILE_SIZE_BYTES",
            "value": str(config_dict["MIN_FILE_SIZE_BYTES"]),
        },
        {"name": "USE_PLUGINS", "value": "True"},
        {"name": "NECESSARY_STRING", "value": config_dict["NECESSARY_STRING"]},
        {"name": "DOWNLOAD_FILES", "value": config_dict["DOWNLOAD_FILES"]},
    ]
    return task_definition


def generate_fiji_task_definition(config_dict):
    task_definition = TASK_DEFINITION.copy()
    sqs = boto3.client("sqs")
    queue_name = get_queue_url(sqs)
    task_definition["containerDefinitions"][0]["environment"] += [
        {"name": "APP_NAME", "value": config_dict["APP_NAME"]},
        {"name": "SQS_QUEUE_URL", "value": queue_name},
        {"name": "AWS_ACCESS_KEY_ID", "value": os.environ["MY_AWS_ACCESS_KEY_ID"]},
        {
            "name": "AWS_SECRET_ACCESS_KEY",
            "value": os.environ["MY_AWS_SECRET_ACCESS_KEY"],
        },
        {"name": "AWS_BUCKET", "value": AWS_BUCKET},
        {"name": "LOG_GROUP_NAME", "value": LOG_GROUP_NAME},
        {
            "name": "EXPECTED_NUMBER_FILES",
            "value": str(config_dict["EXPECTED_NUMBER_FILES"]),
        },
        {"name": "ECS_CLUSTER", "value": ECS_CLUSTER},
        {
            "name": "MIN_FILE_SIZE_BYTES",
            "value": str(config_dict["MIN_FILE_SIZE_BYTES"]),
        },
        {"name": "SCRIPT_DOWNLOAD_URL", "value": config_dict["SCRIPT_DOWNLOAD_URL"]},
    ]
    return task_definition


def update_ecs_task_definition(ecs, ECS_TASK_NAME, config_dict, cellprofiler):
    if cellprofiler:
        task_definition = generate_task_definition(config_dict)
    else:
        task_definition = generate_fiji_task_definition(config_dict)
    ecs.register_task_definition(
        family=ECS_TASK_NAME,
        containerDefinitions=task_definition["containerDefinitions"],
    )
    print("Task definition registered")


def get_or_create_cluster(ecs):
    data = ecs.list_clusters()
    cluster = [clu for clu in data["clusterArns"] if clu.endswith(ECS_CLUSTER)]
    if len(cluster) == 0:
        ecs.create_cluster(clusterName=ECS_CLUSTER)
        time.sleep(WAIT_TIME)
        print(("Cluster " + ECS_CLUSTER + " created"))
    else:
        print(("Cluster " + ECS_CLUSTER + " exists"))


def create_or_update_ecs_service(ecs, ECS_SERVICE_NAME, ECS_TASK_NAME):
    # Create the service with no workers (0 desired count)
    data = ecs.list_services(cluster=ECS_CLUSTER)
    service = [srv for srv in data["serviceArns"] if srv.endswith(ECS_SERVICE_NAME)]
    if len(service) > 0:
        print("Service exists. Removing")
        ecs.delete_service(cluster=ECS_CLUSTER, service=ECS_SERVICE_NAME)
        print(("Removed service " + ECS_SERVICE_NAME))
        time.sleep(WAIT_TIME)

    print("Creating new service")
    ecs.create_service(
        cluster=ECS_CLUSTER,
        serviceName=ECS_SERVICE_NAME,
        taskDefinition=ECS_TASK_NAME,
        desiredCount=0,
    )
    print("Service created")


def get_queue_url(sqs):
    result = sqs.list_queues()
    if "QueueUrls" in list(result.keys()):
        for u in result["QueueUrls"]:
            if u.split("/")[-1] == SQS_QUEUE_NAME:
                return u
    return None


def get_or_create_queue(sqs, config_dict):
    SQS_DEFINITION = {
        "DelaySeconds": "0",
        "MaximumMessageSize": "262144",
        "MessageRetentionPeriod": "1209600",
        "ReceiveMessageWaitTimeSeconds": "0",
        "RedrivePolicy": '{"deadLetterTargetArn":"'
        + SQS_DEAD_LETTER_QUEUE
        + '","maxReceiveCount":"10"}',
        "VisibilityTimeout": str(config_dict["SQS_MESSAGE_VISIBILITY"]),
    }
    u = get_queue_url(sqs)
    if u is None:
        print("Creating queue")
        sqs.create_queue(QueueName=SQS_QUEUE_NAME, Attributes=SQS_DEFINITION)
        time.sleep(WAIT_TIME)
    else:
        print("Queue exists")


def loadConfig(configFile):
    data = None
    with open(configFile, "r") as conf:
        data = json.load(conf)
    return data


def generateECSconfig(ECS_CLUSTER, config_dict, AWS_BUCKET, s3client):
    configfile = open("/tmp/configtemp.config", "w")
    configfile.write("ECS_CLUSTER=" + ECS_CLUSTER + "\n")
    configfile.write('ECS_AVAILABLE_LOGGING_DRIVERS=["json-file","awslogs"]')
    configfile.close()
    s3client.upload_file(
        "/tmp/configtemp.config",
        AWS_BUCKET,
        "ecsconfigs/" + config_dict["APP_NAME"] + "_ecs.config",
    )
    os.remove("/tmp/configtemp.config")
    return (
        "s3://" + AWS_BUCKET + "/ecsconfigs/" + config_dict["APP_NAME"] + "_ecs.config"
    )


def generateUserData(ecsConfigFile, dockerBaseSize):
    config_str = "#!/bin/bash \n"
    config_str += "sudo yum install -y aws-cli \n"
    config_str += "sudo yum install -y awslogs \n"
    config_str += "aws s3 cp " + ecsConfigFile + " /etc/ecs/ecs.config"

    boothook_str = "#!/bin/bash \n"
    boothook_str += (
        "echo 'OPTIONS="
        + '"${OPTIONS} --storage-opt dm.basesize='
        + str(dockerBaseSize)
        + 'G"'
        + "' >> /etc/sysconfig/docker"
    )

    config = MIMEText(config_str, _subtype="x-shellscript")
    config.add_header("Content-Disposition", "attachment", filename="config_temp.txt")

    boothook = MIMEText(boothook_str, _subtype="cloud-boothook")
    boothook.add_header(
        "Content-Disposition", "attachment", filename="boothook_temp.txt"
    )

    pre_user_data = MIMEMultipart()
    pre_user_data.attach(boothook)
    pre_user_data.attach(config)

    pre_user_data_string = pre_user_data.as_string()
    return b64encode(pre_user_data_string.encode("utf-8")).decode("utf-8")


def removequeue(queueName):
    sqs = boto3.client("sqs")
    queueoutput = sqs.list_queues(QueueNamePrefix=queueName)
    if len(queueoutput["QueueUrls"]) == 1:
        queueUrl = queueoutput["QueueUrls"][0]
    else:  # In case we have "AnalysisQueue" and "AnalysisQueue1" and only want to delete the first of those
        for eachUrl in queueoutput["QueueUrls"]:
            if eachUrl.split("/")[-1] == queueName:
                queueUrl = eachUrl
    sqs.delete_queue(QueueUrl=queueUrl)


def deregistertask(taskName, ecs):
    taskArns = ecs.list_task_definitions(familyPrefix=taskName, status="ACTIVE")
    for eachtask in taskArns["taskDefinitionArns"]:
        fulltaskname = eachtask.split("/")[-1]
        ecs.deregister_task_definition(taskDefinition=fulltaskname)


def removeClusterIfUnused(clusterName, ecs):
    if clusterName != "default":
        # never delete the default cluster
        result = ecs.describe_clusters(clusters=[clusterName])
        if (
            sum(
                [
                    result["clusters"][0]["pendingTasksCount"],
                    result["clusters"][0]["runningTasksCount"],
                    result["clusters"][0]["activeServicesCount"],
                    result["clusters"][0]["registeredContainerInstancesCount"],
                ]
            )
            == 0
        ):
            ecs.delete_cluster(cluster=clusterName)


def downscaleSpotFleet(queue, spotFleetID, ec2):
    visible, nonvisible = queue.returnLoad()
    if visible > 0:
        return
    else:
        status = ec2.describe_spot_fleet_instances(SpotFleetRequestId=spotFleetID)
        if nonvisible < len(status["ActiveInstances"]):
            ec2.modify_spot_fleet_request(
                ExcessCapacityTerminationPolicy="noTermination",
                SpotFleetRequestId=spotFleetID,
                TargetCapacity=nonvisible,
            )


def export_logs(logs, loggroupId, starttime, bucketId):
    result = logs.create_export_task(
        taskName=loggroupId,
        logGroupName=loggroupId,
        fromTime=starttime,
        to=time.time() * 1000,
        destination=bucketId,
        destinationPrefix="exportedlogs/" + loggroupId,
    )

    logExportId = result["taskId"]

    while True:
        result = describe_export_tasks(taskId=logExportId)
        if result["exportTasks"][0]["status"]["code"] != "PENDING":
            if result["exportTasks"][0]["status"]["code"] != "RUNNING":
                print((result["exportTasks"][0]["status"]["code"]))
                break
        time.sleep(30)


#################################
# CLASS TO HANDLE SQS QUEUE
#################################


class JobQueue:
    def __init__(self, name=None):
        self.sqs = boto3.resource("sqs")
        if name == None:
            self.queue = self.sqs.get_queue_by_name(QueueName=SQS_QUEUE_NAME)
        else:
            self.queue = self.sqs.get_queue_by_name(QueueName=name)
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print(("Batch sent. Message ID:", response.get("MessageId")))

    def pendingLoad(self):
        self.queue.load()
        visible = int(self.queue.attributes["ApproximateNumberOfMessages"])
        nonVis = int(self.queue.attributes["ApproximateNumberOfMessagesNotVisible"])
        if [visible, nonVis] != [self.pending, self.inProcess]:
            self.pending = visible
            self.inProcess = nonVis
            d = datetime.datetime.now()
            print((d, "In process:", nonVis, "Pending", visible))
        if visible + nonVis > 0:
            return True
        else:
            return False

    def returnLoad(self):
        self.queue.load()
        visible = int(self.queue.attributes["ApproximateNumberOfMessages"])
        nonVis = int(self.queue.attributes["ApproximateNumberOfMessagesNotVisible"])
        return visible, nonVis


#################################
# SERVICE 1: SETUP
#################################


def setup(config_dict, cellprofiler):
    print(config_dict["APP_NAME"], "setup started")
    ECS_TASK_NAME = config_dict["APP_NAME"] + "Task"
    ECS_SERVICE_NAME = config_dict["APP_NAME"] + "Service"
    sqs = boto3.client("sqs")
    get_or_create_queue(sqs, config_dict)
    ecs = boto3.client("ecs")
    get_or_create_cluster(ecs)
    update_ecs_task_definition(ecs, ECS_TASK_NAME, config_dict, cellprofiler)
    create_or_update_ecs_service(ecs, ECS_SERVICE_NAME, ECS_TASK_NAME)
    return config_dict["APP_NAME"]


#################################
# SERVICE 2: SUBMIT JOB
#################################


def submitJob():
    if len(sys.argv) < 3:
        print("Use: run.py submitJob jobfile")
        sys.exit()

    # Step 1: Read the job configuration file
    jobInfo = loadConfig(sys.argv[2])
    if "output_structure" not in list(
        jobInfo.keys()
    ):  # backwards compatibility for 1.0.0
        jobInfo["output_structure"] = ""
    templateMessage = {
        "Metadata": "",
        "pipeline": jobInfo["pipeline"],
        "output": jobInfo["output"],
        "input": jobInfo["input"],
        "data_file": jobInfo["data_file"],
        "output_structure": jobInfo["output_structure"],
    }

    # Step 2: Reach the queue and schedule tasks
    print("Contacting queue")
    queue = JobQueue()
    print("Scheduling tasks")
    for batch in jobInfo["groups"]:
        # support Metadata passed as either a single string or as a list
        try:  # single string ('canonical' DCP)
            templateMessage["Metadata"] = batch["Metadata"]
        except KeyError:  # list of parameters (cellprofiler --print-groups)
            templateMessage["Metadata"] = batch
        queue.scheduleBatch(templateMessage)
    print("Job submitted. Check your queue")


#################################
# SERVICE 3: START CLUSTER
#################################


def startCluster(fleetfile, njobs, config_dict):

    print(njobs, "jobs to do")

    try:
        DOCKER_CORES = float(config_dict["DOCKER_CORES"])
    except:
        DOCKER_CORES = 1.0
    nmachines = min(
        200, int(numpy.ceil(float(njobs) / (DOCKER_CORES * TASKS_PER_MACHINE)))
    )

    print(nmachines, "machines being started to run them")

    # Step 1: set up the configuration files
    s3client = boto3.client("s3")
    ecsConfigFile = generateECSconfig(
        ECS_CLUSTER, config_dict["APP_NAME"], AWS_BUCKET, s3client
    )
    spotfleetConfig = loadConfig(fleetfile)
    spotfleetConfig["ValidFrom"] = datetime.datetime.now().replace(microsecond=0)
    spotfleetConfig["ValidUntil"] = (
        datetime.datetime.now() + datetime.timedelta(days=365)
    ).replace(microsecond=0)
    spotfleetConfig["TargetCapacity"] = nmachines
    spotfleetConfig["SpotPrice"] = "%.2f" % config_dict["MACHINE_PRICE"]
    DOCKER_BASE_SIZE = int(config_dict["EBS_VOL_SIZE"]) - 2
    userData = generateUserData(ecsConfigFile, DOCKER_BASE_SIZE)
    MACHINE_TYPE = "[" + config_dict["MACHINE_TYPE"] + "]"
    for LaunchSpecification in range(0, len(spotfleetConfig["LaunchSpecifications"])):
        spotfleetConfig["LaunchSpecifications"][LaunchSpecification][
            "UserData"
        ] = userData
        spotfleetConfig["LaunchSpecifications"][LaunchSpecification][
            "BlockDeviceMappings"
        ][1]["Ebs"]["VolumeSize"] = config_dict["EBS_VOL_SIZE"]
        spotfleetConfig["LaunchSpecifications"][LaunchSpecification][
            "InstanceType"
        ] = MACHINE_TYPE[LaunchSpecification]

    # Step 2: make the spot fleet request
    ec2client = boto3.client("ec2")
    requestInfo = ec2client.request_spot_fleet(SpotFleetRequestConfig=spotfleetConfig)
    print("Request in process. Wait until your machines are available in the cluster.")
    print(("SpotFleetRequestId", requestInfo["SpotFleetRequestId"]))

    # Step 3: Make the monitor
    starttime = str(int(time.time() * 1000))
    createMonitor = open(
        "/tmp/" + config_dict["APP_NAME"] + "SpotFleetRequestId.json", "w"
    )
    createMonitor.write(
        '{"MONITOR_FLEET_ID" : "' + requestInfo["SpotFleetRequestId"] + '",\n'
    )
    createMonitor.write('"MONITOR_APP_NAME" : "' + config_dict["APP_NAME"] + '",\n')
    createMonitor.write('"MONITOR_ECS_CLUSTER" : "' + ECS_CLUSTER + '",\n')
    createMonitor.write('"MONITOR_QUEUE_NAME" : "' + SQS_QUEUE_NAME + '",\n')
    createMonitor.write('"MONITOR_BUCKET_NAME" : "' + AWS_BUCKET + '",\n')
    createMonitor.write('"MONITOR_LOG_GROUP_NAME" : "' + LOG_GROUP_NAME + '",\n')
    createMonitor.write('"MONITOR_START_TIME" : "' + starttime + '"}\n')
    createMonitor.close()

    # Step 4: Create a log group for this app and date if one does not already exist
    logclient = boto3.client("logs")
    loggroupinfo = logclient.describe_log_groups(logGroupNamePrefix=LOG_GROUP_NAME)
    groupnames = [d["logGroupName"] for d in loggroupinfo["logGroups"]]
    if LOG_GROUP_NAME not in groupnames:
        logclient.create_log_group(logGroupName=LOG_GROUP_NAME)
        logclient.put_retention_policy(logGroupName=LOG_GROUP_NAME, retentionInDays=60)
    if LOG_GROUP_NAME + "_perInstance" not in groupnames:
        logclient.create_log_group(logGroupName=LOG_GROUP_NAME + "_perInstance")
        logclient.put_retention_policy(
            logGroupName=LOG_GROUP_NAME + "_perInstance", retentionInDays=60
        )

    # Step 5: update the ECS service to be ready to inject docker containers in EC2 instances
    print("Updating service")
    ecs = boto3.client("ecs")
    ecs.update_service(
        cluster=ECS_CLUSTER,
        service=config_dict["APP_NAME"] + "Service",
        desiredCount=nmachines * TASKS_PER_MACHINE,
    )
    print("Service updated.")

    # Step 6: Monitor the creation of the instances until all are present
    status = ec2client.describe_spot_fleet_instances(
        SpotFleetRequestId=requestInfo["SpotFleetRequestId"]
    )
    while len(status["ActiveInstances"]) < CLUSTER_MACHINES:
        # First check to make sure there's not a problem
        print((datetime.datetime.now().replace(microsecond=0)))
        # hackery to deal with time zones
        errorcheck = ec2client.describe_spot_fleet_request_history(
            SpotFleetRequestId=requestInfo["SpotFleetRequestId"],
            EventType="error",
            StartTime=(datetime.datetime.now() - datetime.timedelta(hours=4)).replace(
                microsecond=0
            ),
        )
        if len(errorcheck["HistoryRecords"]) != 0:
            print(
                "Your spot fleet request is causing an error and is now being cancelled.  Please check your configuration and try again"
            )
            for eacherror in errorcheck["HistoryRecords"]:
                print(
                    (
                        eacherror["EventInformation"]["EventSubType"]
                        + " : "
                        + eacherror["EventInformation"]["EventDescription"]
                    )
                )
            ec2client.cancel_spot_fleet_requests(
                SpotFleetRequestIds=[requestInfo["SpotFleetRequestId"]],
                TerminateInstances=True,
            )
            return

        # If everything seems good, just bide your time until you're ready to go
        print(".")
        time.sleep(20)
        status = ec2client.describe_spot_fleet_instances(
            SpotFleetRequestId=requestInfo["SpotFleetRequestId"]
        )

    print("Spot fleet successfully created. Your job should start in a few minutes.")


#################################
# SERVICE 4: MONITOR JOB
#################################


def upload_monitor(bucket_name, prefix, batch, step, config_dict):
    s3 = boto3.client("s3")
    json_on_bucket_name = (
        prefix
        + "monitors/"
        + batch
        + "/"
        + step
        + "/"
        + config_dict["APP_NAME"]
        + "SpotFleetRequestId.json"
    )
    with open("/tmp/" + config_dict["APP_NAME"] + "SpotFleetRequestId.json", "rb") as a:
        s3.put_object(Body=a, Bucket=bucket_name, Key=json_on_bucket_name)


def monitor(config_dict):

    monitorInfo = loadConfig(
        "/tmp/" + config_dict["APP_NAME"] + "SpotFleetRequestId.json"
    )
    monitorcluster = monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp = monitorInfo["MONITOR_APP_NAME"]
    fleetId = monitorInfo["MONITOR_FLEET_ID"]
    queueId = monitorInfo["MONITOR_QUEUE_NAME"]

    ec2 = boto3.client("ec2")
    cloud = boto3.client("cloudwatch")
    # Step 1: Create job and count messages periodically
    queue = JobQueue(name=queueId)
    while queue.pendingLoad():
        # Once an hour (except at midnight) check for terminated machines and delete their alarms.
        # This is slooooooow, which is why we don't just do it at the end
        curtime = datetime.datetime.now().strftime("%H%M")
        if curtime[-2:] == "00":
            if curtime[:2] != "00":
                killdeadAlarms(fleetId, monitorapp, ec2, cloud)
        # Once every 10 minutes, check if all jobs are in process, and if so scale the spot fleet size to match
        # the number of jobs still in process WITHOUT force terminating them.
        # This can help keep costs down if, for example, you start up 100+ machines to run a large job, and
        # 1-10 jobs with errors are keeping it rattling around for hours.
        if curtime[-1:] == "9":
            downscaleSpotFleet(queue, fleetId, ec2)
        time.sleep(MONITOR_TIME)

    # Step 2: When no messages are pending, stop service
    # Reload the monitor info, because for long jobs new fleets may have been started, etc
    monitorInfo = loadConfig(
        "/tmp/" + config_dict["APP_NAME"] + "SpotFleetRequestId.json"
    )
    monitorcluster = monitorInfo["MONITOR_ECS_CLUSTER"]
    monitorapp = monitorInfo["MONITOR_APP_NAME"]
    fleetId = monitorInfo["MONITOR_FLEET_ID"]
    queueId = monitorInfo["MONITOR_QUEUE_NAME"]
    bucketId = monitorInfo["MONITOR_BUCKET_NAME"]
    loggroupId = monitorInfo["MONITOR_LOG_GROUP_NAME"]
    starttime = monitorInfo["MONITOR_START_TIME"]

    ecs = boto3.client("ecs")
    ecs.update_service(
        cluster=monitorcluster, service=monitorapp + "Service", desiredCount=0
    )
    print("Service has been downscaled")

    # Step3: Delete the alarms from active machines and machines that have died since the last sweep
    # This is in a try loop, because while it is important, we don't want to not stop the spot fleet
    try:
        result = ec2.describe_spot_fleet_instances(SpotFleetRequestId=fleetId)
        instancelist = result["ActiveInstances"]
        while len(instancelist) > 0:
            to_del = instancelist[:100]
            del_alarms = [monitorapp + "_" + x["InstanceId"] for x in to_del]
            cloud.delete_alarms(AlarmNames=del_alarms)
            time.sleep(10)
            instancelist = instancelist[100:]
        killdeadAlarms(fleetId, monitorapp)
    except:
        pass

    # Step 4: Read spot fleet id and terminate all EC2 instances
    print("Shutting down spot fleet", fleetId)
    ec2.cancel_spot_fleet_requests(
        SpotFleetRequestIds=[fleetId], TerminateInstances=True
    )
    print("Job done.")

    # Step 5. Release other resources
    # Remove SQS queue, ECS Task Definition, ECS Service
    ECS_TASK_NAME = monitorapp + "Task"
    ECS_SERVICE_NAME = monitorapp + "Service"
    print("Deleting existing queue.")
    removequeue(queueId)
    print("Deleting service")
    ecs.delete_service(cluster=monitorcluster, service=ECS_SERVICE_NAME)
    print("De-registering task")
    deregistertask(ECS_TASK_NAME, ecs)
    print("Removing cluster if it's not the default and not otherwise in use")
    removeClusterIfUnused(monitorcluster, ecs)

    # Step 6: Export the logs to S3
    logs = boto3.client("logs")

    print("Transfer of CellProfiler logs to S3 initiated")
    export_logs(logs, loggroupId, starttime, bucketId)

    print("Transfer of per-instance to S3 initiated")
    export_logs(logs, loggroupId + "_perInstance", starttime, bucketId)

    print("All export tasks done")

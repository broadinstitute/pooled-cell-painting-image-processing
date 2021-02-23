# Constants (User configurable)

APP_NAME = '2018_11_20_Periscope_X_BarcodingStitching'                # Used to generate derivative names unique to the application.

# DOCKER REGISTRY INFORMATION:
DOCKERHUB_TAG = 'cellprofiler/distributed-fiji:latest'

# AWS GENERAL SETTINGS:
AWS_REGION = 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'key.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'dummybucket'

# EC2 AND ECS INFORMATION:
ECS_CLUSTER = 'default_cluster'
CLUSTER_MACHINES = 1
TASKS_PER_MACHINE = 1
MACHINE_TYPE = ['m4.2xlarge']
MACHINE_PRICE = 0.25
EBS_VOL_SIZE = 800                       # In GB.  Minimum allowed is 22.  Docker will get this - 2 GB
DOWNLOAD_FILES = 'False'

# DOCKER INSTANCE RUNNING ENVIRONMENT:
MEMORY = 31000                           # Memory assigned to the docker container in MB
SCRIPT_DOWNLOAD_URL = 'https://dummybucket.s3.amazonaws.com/projects/2018_11_20_Periscope_X/workspace/software/BatchStitchPooledCellPainting_StitchAndCrop_Headless.py'

# SQS QUEUE INFORMATION:
SQS_QUEUE_NAME = APP_NAME + 'Queue'
SQS_MESSAGE_VISIBILITY = 180*60           # Timeout (secs) for messages in flight (average time to be processed)
SQS_DEAD_LETTER_QUEUE = 'arn:aws:sqs:us-east-1:XXXXXXXXXXXX:DeadMessages'

# LOG GROUP INFORMATION:
LOG_GROUP_NAME = APP_NAME

# REDUNDANCY CHECKS
EXPECTED_NUMBER_FILES = 510    #What is the number of files that trigger that a job completed successfully?
MIN_FILE_SIZE_BYTES = 1      #What is the minimal number of bytes an object should be to "count"?
NECESSARY_STRING = ''        #Is there any string that should be in the file name to "count"?

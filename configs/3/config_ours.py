# Constants (User configurable)

APP_NAME = '2018_11_20_Periscope_X_PaintingSegmentationCheck'                # Used to generate derivative names unique to the application.

# DOCKER REGISTRY INFORMATION:
DOCKERHUB_TAG = 'cellprofiler/distributed-cellprofiler:2.0.0_4.0.7'

# AWS GENERAL SETTINGS:
AWS_REGION = 'us-east-1'
AWS_PROFILE = 'default'                 # The same profile used by your AWS CLI installation
SSH_KEY_NAME = 'key.pem'      # Expected to be in ~/.ssh
AWS_BUCKET = 'dummybucket'

# EC2 AND ECS INFORMATION:
ECS_CLUSTER = 'default_cluster'
CLUSTER_MACHINES = 1
TASKS_PER_MACHINE = 1
MACHINE_TYPE = ['m4.xlarge']
MACHINE_PRICE = 0.10
EBS_VOL_SIZE = 200                       # In GB.  Minimum allowed is 22.
DOWNLOAD_FILES = 'False'

# DOCKER INSTANCE RUNNING ENVIRONMENT:
DOCKER_CORES = 4                        # Number of CellProfiler processes to run inside a docker container
CPU_SHARES = DOCKER_CORES * 1024        # ECS computing units assigned to each docker container (1024 units = 1 core)
MEMORY = 15000                          # Memory assigned to the docker container in MB
SECONDS_TO_START = 3*60                 # Wait before the next CP process is initiated to avoid memory collisions

#SQS QUEUE INFORMATION:
SQS_QUEUE_NAME = APP_NAME + 'Queue'
SQS_MESSAGE_VISIBILITY = 20*60           # Timeout (secs) for messages in flight (average time to be processed)
SQS_DEAD_LETTER_QUEUE = 'arn:aws:sqs:us-east-1:XXXXXXXXXXXX:DeadMessages'

# LOG GROUP INFORMATION:
LOG_GROUP_NAME = APP_NAME

# REDUNDANCY CHECKS
CHECK_IF_DONE_BOOL = 'False'    # True or False- should it check if there are a certain number of non-empty files and delete the job if yes?
EXPECTED_NUMBER_FILES = 5       # What is the number of files that trigger skipping a job?
MIN_FILE_SIZE_BYTES = 1
NECESSARY_STRING = ''           # Is there any string that should be in the file name to "count"?

# PLUGINS
USE_PLUGINS = 'True'

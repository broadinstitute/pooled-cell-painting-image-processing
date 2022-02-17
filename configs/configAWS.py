# AWS GENERAL SETTINGS:
AWS_REGION = "us-east-1"
AWS_PROFILE = "default"  # The same profile used by your AWS CLI installation
SSH_KEY_NAME = "key.pem"  # Expected to be in ~/.ssh
AWS_BUCKET = "dummybucket"

# EC2 AND ECS INFORMATION:
ECS_CLUSTER = "default_cluster"

# SQS QUEUE INFORMATION:
SQS_DEAD_LETTER_QUEUE = "arn:aws:sqs:us-east-1:XXXXXXXXXXXX:DeadMessages"
SQS_DUPLICATE_QUEUE = "PreventOverlappingStarts.fifo"

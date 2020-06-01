import json
import boto3
import string
import os
import posixpath

class JobQueue():

    def __init__(self,name=None):
        self.sqs = boto3.resource('sqs')
        self.queue = self.sqs.get_queue_by_name(QueueName=name)
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print('Batch sent. Message ID:',response.get('MessageId'))


def create_batch_jobs_1(startpath,batchsuffix,illumpipename,platelist):
    #startpath=posixpath.join('projects',topdirname)
    pipelinepath=posixpath.join(startpath,os.path.join('workspace/pipelines',batchsuffix))
    illumoutpath=posixpath.join(startpath,os.path.join(batchsuffix,'illum'))
    datafilepath=posixpath.join(startpath,os.path.join('workspace/load_data_csv',batchsuffix))
    illumqueue = JobQueue('2018_11_20_Periscope_X_IllumPaintingQueue')
    for toillum in platelist:
        templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum,
                                 'pipeline': posixpath.join(pipelinepath,illumpipename),'output': illumoutpath,
                                 'input': pipelinepath, 'data_file':posixpath.join(datafilepath,toillum, 'load_data_pipeline1.csv')}
            
        illumqueue.scheduleBatch(templateMessage_illum)

    print('Illum job submitted. Check your queue')
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


def create_batch_jobs_1(startpath,batchsuffix,illumpipename,platelist, app_name):
    #startpath=posixpath.join('projects',topdirname)
    pipelinepath=posixpath.join(startpath,os.path.join('workspace/pipelines',batchsuffix))
    illumoutpath=posixpath.join(startpath,os.path.join(batchsuffix,'illum'))
    datafilepath=posixpath.join(startpath,os.path.join('workspace/load_data_csv',batchsuffix))
    illumqueue = JobQueue(app_name+'Queue')
    for toillum in platelist:
        templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum,
                                 'pipeline': posixpath.join(pipelinepath,illumpipename),'output': illumoutpath,
                                 'input': pipelinepath, 'data_file':posixpath.join(datafilepath,toillum, 'load_data_pipeline1.csv')}
            
        illumqueue.scheduleBatch(templateMessage_illum)

    print('Illum job submitted. Check your queue')

def create_batch_jobs_2(startpath,batchsuffix,illumpipename,platelist, well_list, app_name):
    #startpath=posixpath.join('projects',topdirname)
    pipelinepath=posixpath.join(startpath,os.path.join('workspace/pipelines',batchsuffix))
    illumoutpath=posixpath.join(startpath,os.path.join(batchsuffix,'images_corrected'))
    datafilepath=posixpath.join(startpath,os.path.join('workspace/load_data_csv',batchsuffix))
    illumqueue = JobQueue(app_name+'Queue')
    for toillum in platelist:
        for well in well_list:
            templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum+',Metadata_Well='+well,
                                     'pipeline': posixpath.join(pipelinepath,illumpipename),'output': illumoutpath,
                                     'input': pipelinepath, 'data_file':posixpath.join(datafilepath,toillum, 'load_data_pipeline2.csv')}
                
            illumqueue.scheduleBatch(templateMessage_illum)

    print('Illum job submitted. Check your queue')
    
def create_batch_jobs_5(startpath,batchsuffix,illumpipename,platelist, expected_cycles, app_name):
    #startpath=posixpath.join('projects',topdirname)
    pipelinepath=posixpath.join(startpath,os.path.join('workspace/pipelines',batchsuffix))
    illumoutpath=posixpath.join(startpath,os.path.join(batchsuffix,'illum'))
    datafilepath=posixpath.join(startpath,os.path.join('workspace/load_data_csv',batchsuffix))
    illumqueue = JobQueue(app_name+'Queue')
    for toillum in platelist:
        for cycle in range(1,expected_cycles+1):
            templateMessage_illum = {'Metadata': 'Metadata_Plate='+toillum+',Metadata_SBSCycle='+str(cycle), 
                                     'pipeline': posixpath.join(pipelinepath,illumpipename),'output': illumoutpath, output_structure:'Metadata_Plate',
                                     'input': pipelinepath, 'data_file':posixpath.join(datafilepath,toillum, 'load_data_pipeline5.csv')}
                
            illumqueue.scheduleBatch(templateMessage_illum)

    print('Illum job submitted. Check your queue')
import json
import boto3
import string
import os
import posixpath


class JobQueue:
    def __init__(self, name=None):
        self.sqs = boto3.resource("sqs")
        self.queue = self.sqs.get_queue_by_name(QueueName=name)
        self.inProcess = -1
        self.pending = -1

    def scheduleBatch(self, data):
        msg = json.dumps(data)
        response = self.queue.send_message(MessageBody=msg)
        print(("Batch sent. Message ID:", response.get("MessageId")))


def create_batch_jobs_1(startpath, batchsuffix, illumpipename, platelist, app_name, SABER_round=False):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    illumoutpath = posixpath.join(startpath, os.path.join(batchsuffix, "illum"))
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    illumqueue = JobQueue(app_name + "Queue")
    if not SABER_round:
        for toillum in platelist:
            templateMessage_illum = {
                "Metadata": "Metadata_Plate=" + toillum,
                "pipeline": posixpath.join(pipelinepath, illumpipename),
                "output": illumoutpath,
                "input": pipelinepath,
                "data_file": posixpath.join(
                    datafilepath, toillum, "load_data_pipeline1.csv"
                ),
            }
            illumqueue.scheduleBatch(templateMessage_illum)
    else:
        for toillum in platelist:
            templateMessage_illum = {
                "Metadata": "Metadata_Plate=" + toillum,
                "pipeline": posixpath.join(pipelinepath, illumpipename),
                "output": illumoutpath,
                "input": pipelinepath,
                "data_file": posixpath.join(
                    datafilepath, toillum, f"load_data_pipeline1_{SABER_round}.csv"
                ),
            }
            illumqueue.scheduleBatch(templateMessage_illum)
    print("Illum job submitted. Check your queue")


def create_batch_jobs_2(
    startpath, batchsuffix, illumpipename, plate_well_dict, app_name, num_series
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    illumoutpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_corrected/painting")
    )
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    illumqueue = JobQueue(app_name + "Queue")
    for toillum in plate_well_dict.keys():
        for well in plate_well_dict[toillum]:
            for site in range(0, num_series+1):
                templateMessage_illum = {
                    "Metadata": f"Metadata_Plate={toillum},Metadata_Well={well},Metadata_Site={site}",
                    "pipeline": posixpath.join(pipelinepath, illumpipename),
                    "output": illumoutpath,
                    "input": pipelinepath,
                    "data_file": posixpath.join(
                        datafilepath, toillum, "load_data_pipeline2.csv"
                    ),
                }
                illumqueue.scheduleBatch(templateMessage_illum)
    print("Illum job submitted. Check your queue")


def create_batch_jobs_3(
    startpath, batchsuffix, segmentpipename, plate_and_well_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    segmentoutpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_segmentation")
    )
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    segmentqueue = JobQueue(app_name + "Queue")
    for tosegment in plate_and_well_list:
        templateMessage_segment = {
            "Metadata": "Metadata_Plate="
            + tosegment[0]
            + ",Metadata_Well="
            + tosegment[1],
            "pipeline": posixpath.join(pipelinepath, segmentpipename),
            "output": segmentoutpath,
            "output_structure": "Metadata_Plate",
            "input": pipelinepath,
            "data_file": posixpath.join(
                datafilepath, tosegment[0], "load_data_pipeline3.csv"
            ),
        }
        segmentqueue.scheduleBatch(templateMessage_segment)
    print("Segment check job submitted. Check your queue")


def create_batch_jobs_3A(
    startpath, batchsuffix, segmentApipename, platelist, well_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    segmentAoutpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_segmentation/troubleshoot")
    )
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    segmentAqueue = JobQueue(app_name + "Queue")
    for totroubleshoot in platelist:
        for well in well_list:
            templateMessage_segmentA = {
                "Metadata": "Metadata_Plate="
                + totroubleshoot
                + ",Metadata_Well="
                + well,
                "pipeline": posixpath.join(pipelinepath, segmentApipename),
                "output": segmentAoutpath,
                "input": pipelinepath,
                "data_file": posixpath.join(
                    datafilepath, totroubleshoot, "load_data_pipeline3A.csv"
                ),
            }
            segmentAqueue.scheduleBatch(templateMessage_segmentA)
    print("Segment Troubleshoot A job submitted. Check your queue")


def create_batch_jobs_3B(
    startpath, batchsuffix, segmentpipename, plate_and_well_list, site_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    segmentoutpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_segmentation")
    )
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    segmentBqueue = JobQueue(app_name + "Queue")
    for tosegment in plate_and_well_list:
        for site in site_list:
            templateMessage_segmentB = {
                "Metadata": "Metadata_Plate="
                + tosegment[0]
                + ",Metadata_Well="
                + tosegment[1]
                + ",Metadata_Site="
                + str(site),
                "pipeline": posixpath.join(pipelinepath, segmentpipename),
                "output": segmentoutpath,
                "output_structure": "Metadata_Plate",
                "input": pipelinepath,
                "data_file": posixpath.join(
                    datafilepath, tosegment[0], "load_data_pipeline3B.csv"
                ),
            }
            segmentBqueue.scheduleBatch(templateMessage_segmentB)
    print("Segment Troubleshoot B job submitted. Check your queue")


def create_batch_jobs_4(
    bucket_name,
    startpath,
    batchsuffix,
    metadata,
    plate_and_well_list,
    app_name,
    tileperside=10,
    final_tile_size=5500,
    xoffset_tiles=0,
    yoffset_tiles=0,
    compress="False",
    quarter_if_round="True",
):
    step_to_stitch = "images_corrected"
    local_start_path = posixpath.join("/home/ubuntu/bucket", startpath)
    if "round_or_square" in list(metadata.keys()):
        round_or_square = metadata["round_or_square"]
    else:  # Backwards compatibility for old square runs
        round_or_square = "square"
    stitchqueue = JobQueue(app_name + "Queue")
    stitchMessage = {
        "Metadata": "",
        "output_file_location": posixpath.join(startpath, batchsuffix),
        "shared_metadata": {
            "input_file_location": local_start_path,
            "step_to_stitch": step_to_stitch,
            "scalingstring": "1",
            "overlap_pct": metadata["overlap_pct"],
            "size": "1480",
            "rows": metadata["painting_rows"],
            "columns": metadata["painting_columns"],
            "imperwell": metadata["painting_imperwell"],
            "stitchorder": metadata["stitchorder"],
            "channame": "DNA",
            "tileperside": str(tileperside),
            "awsdownload": "True",
            "bucketname": bucket_name,
            "localtemp": "local_temp",
            "round_or_square": round_or_square,
            "quarter_if_round": quarter_if_round,
            "final_tile_size": str(final_tile_size),
            "xoffset_tiles": str(xoffset_tiles),
            "yoffset_tiles": str(yoffset_tiles),
            "compress": compress,
        },
    }
    for tostitch in plate_and_well_list:
        if "_" not in tostitch[1]:
            well = "Well_" + tostitch[1][4:]
        else:
            well = tostitch[1]
        stitchMessage["Metadata"] = {
            "subdir": posixpath.join(
                batchsuffix,
                step_to_stitch,
                "painting",
                tostitch[0] + "-" + tostitch[1],
            ),
            "out_subdir_tag": tostitch[0] + "_" + tostitch[1],
            "filterstring": well,
            "downloadfilter": "*" + well + "*",
        }
        stitchqueue.scheduleBatch(stitchMessage)
    print("Stitching job submitted. Check your queue")


def create_batch_jobs_5(
    startpath, batchsuffix, illumpipename, platelist, expected_cycles, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    illumoutpath = posixpath.join(startpath, os.path.join(batchsuffix, "illum"))
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    illumqueue = JobQueue(app_name + "Queue")
    for toillum in platelist:
        for cycle in range(1, expected_cycles + 1):
            templateMessage_illum = {
                "Metadata": "Metadata_Plate="
                + toillum
                + ",Metadata_SBSCycle="
                + str(cycle),
                "pipeline": posixpath.join(pipelinepath, illumpipename),
                "output": illumoutpath,
                "output_structure": "Metadata_Plate",
                "input": pipelinepath,
                "data_file": posixpath.join(
                    datafilepath, toillum, "load_data_pipeline5.csv"
                ),
            }
            illumqueue.scheduleBatch(templateMessage_illum)
    print("Illum job submitted. Check your queue")


def create_batch_jobs_6(
    startpath,
    batchsuffix,
    illumpipename,
    plate_and_well_list,
    app_name,
    one_or_many,
    num_series,
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    illumoutpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_aligned/barcoding")
    )
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    illumqueue = JobQueue(app_name + "Queue")
    for toillum in plate_and_well_list:
        if one_or_many == "one":
            for arb in range(19):  # later do this per site
                templateMessage_illum = {
                    "Metadata": "Metadata_Plate="
                    + toillum[0]
                    + ",Metadata_Well="
                    + toillum[1]
                    + ",Metadata_ArbitraryGroup="
                    + str(arb),
                    "pipeline": posixpath.join(pipelinepath, illumpipename),
                    "output": illumoutpath,
                    "output_structure": "Metadata_Plate-Metadata_Well",
                    "input": pipelinepath,
                    "data_file": posixpath.join(
                        datafilepath, toillum[0], "load_data_pipeline6.csv"
                    ),
                }
                illumqueue.scheduleBatch(templateMessage_illum)
        else:
            for series in range(int(num_series)):
                templateMessage_illum = {
                    "Metadata": "Metadata_Plate="
                    + toillum[0]
                    + ",Metadata_Well="
                    + toillum[1]
                    + ",Metadata_Site="
                    + str(series),
                    "pipeline": posixpath.join(pipelinepath, illumpipename),
                    "output": illumoutpath,
                    "output_structure": "Metadata_Plate-Metadata_Well-Metadata_Site",
                    "input": pipelinepath,
                    "data_file": posixpath.join(
                        datafilepath, toillum[0], "load_data_pipeline6.csv"
                    ),
                }
                illumqueue.scheduleBatch(templateMessage_illum)
    print("Illum job submitted. Check your queue")


def create_batch_jobs_6A(
    startpath, batchsuffix, pipeline_name_list, plate_and_well_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    illumoutpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_aligned_troubleshooting/barcoding")
    )
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    illumqueue = JobQueue(app_name + "Queue")
    for toillum in plate_and_well_list:
        for arb in [0]:  # later do this per site
            for illumpipename in pipeline_name_list:
                templateMessage_illum = {
                    "Metadata": "Metadata_Plate="
                    + toillum[0]
                    + ",Metadata_Well="
                    + toillum[1]
                    + ",Metadata_ArbitraryGroup="
                    + str(arb),
                    "pipeline": posixpath.join(pipelinepath, illumpipename),
                    "output": posixpath.join(illumoutpath, illumpipename[:-7]),
                    "output_structure": "Metadata_Plate-Metadata_Well",
                    "input": pipelinepath,
                    "data_file": posixpath.join(
                        datafilepath, toillum[0], "load_data_pipeline6.csv"
                    ),
                }
                illumqueue.scheduleBatch(templateMessage_illum)
    print("Illum job submitted. Check your queue")


def create_batch_jobs_7(
    startpath, batchsuffix, pipename, plate_and_well_list, site_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    outpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_corrected/barcoding")
    )
    inpath = posixpath.join(startpath, os.path.join("workspace/metadata", batchsuffix))
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    correctqueue = JobQueue(app_name + "Queue")
    for tocorrect in plate_and_well_list:
        for site in site_list:  # later do this per site
            templateMessage_correct = {
                "Metadata": "Metadata_Plate="
                + tocorrect[0]
                + ",Metadata_Well="
                + tocorrect[1]
                + ",Metadata_Site="
                + str(site),
                "pipeline": posixpath.join(pipelinepath, pipename),
                "output": outpath,
                "input": inpath,
                "data_file": posixpath.join(
                    datafilepath, tocorrect[0], "load_data_pipeline7.csv"
                ),
            }
            correctqueue.scheduleBatch(templateMessage_correct)
    print("Correction job submitted. Check your queue")


def create_batch_jobs_7A(
    startpath, batchsuffix, pipename, plate_and_well_list, site_list, app_name, skip
):
    site_list = list(range(0, max(site_list), skip))
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    outpath = posixpath.join(
        startpath, os.path.join(batchsuffix, "images_corrected_troubleshooting/")
    )
    inpath = posixpath.join(startpath, os.path.join("workspace/metadata", batchsuffix))
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    correctqueue = JobQueue(app_name + "Queue")
    for tocorrect in plate_and_well_list:
        for site in site_list:  # later do this per site
            templateMessage_correct = {
                "Metadata": "Metadata_Plate="
                + tocorrect[0]
                + ",Metadata_Well="
                + tocorrect[1]
                + ",Metadata_Site="
                + str(site),
                "pipeline": posixpath.join(pipelinepath, pipename),
                "output": outpath,
                "input": inpath,
                "data_file": posixpath.join(
                    datafilepath, tocorrect[0], "load_data_pipeline7.csv"
                ),
            }
            correctqueue.scheduleBatch(templateMessage_correct)
    print("Correction job submitted. Check your queue")


def create_batch_jobs_8(
    bucket_name,
    startpath,
    batchsuffix,
    metadata,
    plate_and_well_list,
    app_name,
    tileperside=10,
    final_tile_size=5500,
    xoffset_tiles=0,
    yoffset_tiles=0,
    compress="False",
    quarter_if_round="True",
):
    step_to_stitch = "images_corrected"
    local_start_path = posixpath.join("/home/ubuntu/bucket", startpath)
    if "round_or_square" in list(metadata.keys()):
        round_or_square = metadata["round_or_square"]
    else:  # Backwards compatibility for old square runs
        round_or_square = "square"
    stitchqueue = JobQueue(app_name + "Queue")
    stitchMessage = {
        "Metadata": "",
        "output_file_location": posixpath.join(startpath, batchsuffix),
        "shared_metadata": {
            "input_file_location": local_start_path,
            "step_to_stitch": step_to_stitch,
            "scalingstring": "1.99",
            "overlap_pct": metadata["overlap_pct"],
            "size": "1480",
            "rows": metadata["barcoding_rows"],
            "columns": metadata["barcoding_columns"],
            "imperwell": metadata["barcoding_imperwell"],
            "stitchorder": metadata["stitchorder"],
            "channame": "DAPI",
            "tileperside": str(tileperside),
            "awsdownload": "True",
            "bucketname": bucket_name,
            "localtemp": "local_temp",
            "round_or_square": round_or_square,
            "quarter_if_round": quarter_if_round,
            "final_tile_size": str(final_tile_size),
            "xoffset_tiles": str(xoffset_tiles),
            "yoffset_tiles": str(yoffset_tiles),
            "compress": compress,
        },
    }
    for tostitch in plate_and_well_list:
        if "_" not in tostitch[1]:
            well = "Well_" + tostitch[1][4:]
        else:
            well = tostitch[1]
        stitchMessage["Metadata"] = {
            "subdir": posixpath.join(batchsuffix, step_to_stitch, "barcoding",),
            "out_subdir_tag": tostitch[0] + "_" + tostitch[1],
            "filterstring": well,
            "downloadfilter": tostitch[0] + "-" + tostitch[1] + "*",
        }
        stitchqueue.scheduleBatch(stitchMessage)
    print("Stitching job submitted. Check your queue")


def create_batch_jobs_8Z(
    bucket_name,
    startpath,
    batchsuffix,
    metadata,
    plate_and_well_list,
    app_name,
    tileperside=10,
    final_tile_size=5500,
    xoffset_tiles=0,
    yoffset_tiles=0,
    compress="False",
    quarter_if_round="True",
):
    step_to_stitch = "images_aligned"
    local_start_path = posixpath.join("/home/ubuntu/bucket", startpath)
    if "round_or_square" in list(metadata.keys()):
        round_or_square = metadata["round_or_square"]
    else:  # Backwards compatibility for old square runs
        round_or_square = "square"
    stitchqueue = JobQueue(app_name + "Queue")
    stitchMessage = {
        "Metadata": "",
        "output_file_location": posixpath.join(startpath, batchsuffix),
        "shared_metadata": {
            "input_file_location": local_start_path,
            "step_to_stitch": step_to_stitch,
            "scalingstring": "1.99",
            "overlap_pct": metadata["overlap_pct"],
            "size": "1480",
            "rows": metadata["barcoding_rows"],
            "columns": metadata["barcoding_columns"],
            "imperwell": metadata["barcoding_imperwell"],
            "stitchorder": metadata["stitchorder"],
            "channame": "DAPI",
            "tileperside": str(tileperside),
            "awsdownload": "True",
            "bucketname": bucket_name,
            "localtemp": "local_temp",
            "round_or_square": round_or_square,
            "quarter_if_round": quarter_if_round,
            "final_tile_size": str(final_tile_size),
            "xoffset_tiles": str(xoffset_tiles),
            "yoffset_tiles": str(yoffset_tiles),
            "compress": compress,
        },
    }
    for tostitch in plate_and_well_list:
        if "_" not in tostitch[1]:
            well = "Well_" + tostitch[1][4:]
        else:
            well = tostitch[1]
        stitchMessage["Metadata"] = {
            "subdir": posixpath.join(batchsuffix, step_to_stitch, "barcoding",),
            "out_subdir_tag": tostitch[0] + "_" + tostitch[1],
            "filterstring": well,
            "downloadfilter": tostitch[0] + "-" + tostitch[1] + "*",
        }
        stitchqueue.scheduleBatch(stitchMessage)
    print("Stitching job submitted. Check your queue")


def create_batch_jobs_8Y(
    startpath, batchsuffix, pipename, plate_and_well_list, site_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    outpath = posixpath.join(
        startpath, os.path.join("workspace/aligncheck", batchsuffix)
    )
    inpath = posixpath.join(startpath, os.path.join("workspace/metadata", batchsuffix))
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    aligncheckqueue = JobQueue(app_name + "Queue")
    for toaligncheck in plate_and_well_list:
        for site in site_list:  # later do this per site
            templateMessage_aligncheck = {
                "Metadata": "Metadata_Plate="
                + toaligncheck[0]
                + ",Metadata_Well="
                + toaligncheck[1]
                + ",Metadata_Site="
                + str(site),
                "pipeline": posixpath.join(pipelinepath, pipename),
                "output": outpath,
                "input": inpath,
                "data_file": posixpath.join(
                    datafilepath, toaligncheck[0], "load_data_pipeline8Y.csv"
                ),
            }
            aligncheckqueue.scheduleBatch(templateMessage_aligncheck)
    print("AlignmentCheck job submitted. Check your queue")


def create_batch_jobs_9(
    startpath, batchsuffix, pipename, plate_and_well_list, site_list, app_name
):
    pipelinepath = posixpath.join(
        startpath, os.path.join("workspace/pipelines", batchsuffix)
    )
    outpath = posixpath.join(startpath, os.path.join("workspace/analysis", batchsuffix))
    inpath = posixpath.join(startpath, os.path.join("workspace/metadata", batchsuffix))
    datafilepath = posixpath.join(
        startpath, os.path.join("workspace/load_data_csv", batchsuffix)
    )
    analysisqueue = JobQueue(app_name + "Queue")
    for toanalyse in plate_and_well_list:
        for site in site_list:  # later do this per site
            templateMessage_analysis = {
                "Metadata": "Metadata_Plate="
                + toanalyse[0]
                + ",Metadata_Well="
                + toanalyse[1]
                + ",Metadata_Site="
                + str(site),
                "pipeline": posixpath.join(pipelinepath, pipename),
                "output": outpath,
                "input": inpath,
                "data_file": posixpath.join(
                    datafilepath, toanalyse[0], "load_data_pipeline9.csv"
                ),
            }
            analysisqueue.scheduleBatch(templateMessage_analysis)
    print("Analysis job submitted. Check your queue")

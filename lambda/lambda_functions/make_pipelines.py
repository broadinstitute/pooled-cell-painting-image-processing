import os
import shutil
import json
import copy
import boto3
from compensation_methods import *

def make_7A_pipeline(compensation_methods, Pipeline7_name, Pipeline7A_name):
    shutil.copy(f"/tmp/{Pipeline7_name}",f"/tmp/{Pipeline7A_name}")

    with open(f"/tmp/{Pipeline7A_name}") as f:
        cppipe=json.load(f)
    f.close()

    # Find original modules, store, and remove them
    lattermodules = []
    done = False
    for entry in range(0,len(cppipe['modules'])):
        if cppipe['modules'][entry]['attributes']['module_name'] == 'CompensateColors':
            CompensateColorsOrig = cppipe['modules'][entry]
            MeasureObjectIntensityOrig = cppipe['modules'][entry + 1]
            CallBarcodesOrig = cppipe['modules'][entry+2]
            done = True
        if done:
            cppipe['modules'].pop(entry)
            cppipe['modules'].pop(entry)
            cppipe['modules'].pop(entry)
            break
    for count in range(0,len(cppipe['modules'])-entry):
        if cppipe['modules'][entry]['attributes']['module_name'] != 'SaveImages':
            if cppipe['modules'][entry]['attributes']['module_name'] != 'ImageMath':
                lattermodules.append(cppipe['modules'][entry])
        cppipe['modules'].pop(entry)

    method_group = 0

    for method in compensation_methods:
        method_dict = eval(method)
        CompensateColors = copy.deepcopy(CompensateColorsOrig)
        MeasureObjectIntensity = copy.deepcopy(MeasureObjectIntensityOrig)
        CallBarcodes = copy.deepcopy(CallBarcodesOrig)
        # Compensate Colors
        CompensateColors['attributes']['module_num'] = CompensateColorsOrig['attributes']['module_num'] + method_group*3
        for setting in range(0, len(CompensateColorsOrig['settings'])):
            text = CompensateColorsOrig['settings'][setting]['text']
            if 'output image name' in text:
                output_name = CompensateColorsOrig['settings'][setting]['value']
                output_name = output_name + f'_{method}'
                CompensateColors['settings'][setting]['value'] = output_name
            if text in method_dict.keys():
                CompensateColors['settings'][setting]['value'] = method_dict[text]
        # MeasureObjectIntensity
        MeasureObjectIntensity['attributes']['module_num'] = MeasureObjectIntensityOrig['attributes']['module_num'] + method_group*3
        img_list = MeasureObjectIntensityOrig['settings'][0]['value'].replace(',','').split()
        img_list = [img + f'_{method}' for img in img_list]
        MeasureObjectIntensity['settings'][0]['value'] = ', '.join(img_list)
        # CallBarcodes
        CallBarcodes['attributes']['module_num'] = CallBarcodesOrig['attributes']['module_num'] + method_group*3
        for setting in range(0,len(CallBarcodesOrig['settings'])):
            text = CallBarcodesOrig['settings'][setting]['text']
            if 'Select one of the measures from Cycle 1' in text:
                output_name = CallBarcodesOrig['settings'][setting]['value']
                output_name = output_name + f'_{method}'
                CallBarcodes['settings'][setting]['value'] = output_name
            if 'Enter the called barcode image name' in text:
                output_name = CallBarcodesOrig['settings'][setting]['value']
                output_name = output_name + f'_{method}'
                CallBarcodes['settings'][setting]['value'] = output_name
            if 'Enter the barcode score image name' in text:
                output_name = CallBarcodesOrig['settings'][setting]['value']
                output_name = output_name + f'_{method}'
                CallBarcodes['settings'][setting]['value'] = output_name
        # Add new modules to file
        cppipe['modules'].append(CompensateColors)
        cppipe['modules'].append(MeasureObjectIntensity)
        cppipe['modules'].append(CallBarcodes)

        method_group += 1

    module_num = CallBarcodesOrig['attributes']['module_num'] + ((method_group-1)*3) + 1
    skipafter = False
    for x in range(0,len(lattermodules)):
        if not skipafter:
            if lattermodules[x]['attributes']['module_name'] == 'MeasureObjectIntensity':
                values = lattermodules[x]['settings'][0]['value']
                values = values.replace(',','').split()
                values = values + ['BarcodeScores_IntValues_' + m for m in compensation_methods]
                values = ', '.join(values)
                lattermodules[x]['settings'][0]['value'] = values
            if lattermodules[x]['attributes']['module_name'] == 'ExportToSpreadsheet':
                skipafter = True
            lattermodules[x]['attributes']['module_num'] = module_num
            module_num += 1
            cppipe['modules'].append(lattermodules[x])

    cppipe['module_count'] = len(cppipe['modules'])

    with open(f"/tmp/{Pipeline7A_name}", 'w') as f:
        json.dump(cppipe, f, indent=4)

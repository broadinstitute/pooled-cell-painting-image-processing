import pandas

def create_CSV_pipeline1(platename, seriesperwell, path, listoffiles):
    columns = ['Metadata_Plate', 'Metadata_Series']
    columns_per_channel = ['PathName_','FileName_','Series_','Frame_']
    channels = ['OrigMito', 'OrigDNA', 'OrigER', 'OrigWGA', 'OrigPhalloidin']
    columns += [col + chan for col in columns_per_channel for chan in channels]
    df = pandas.DataFrame(columns=columns)
    total_file_count = seriesperwell*len(listoffiles)
    df['Metadata_Plate'] = [platename] * total_file_count
    df['Metadata_Series'] = range(seriesperwell) * len(listoffiles)
    for chan in channels:
        df['Series_'+chan] = range(seriesperwell) * len(listoffiles)
        df['PathName_'+chan] = [path] * total_file_count
    file_list_1, file_list_2 = zip(*listoffiles)
    temp_list = [[x] * seriesperwell for x in file_list_1]
    full_list_1 = [x for sublist in temp_list for x in sublist]
    for chan in channels[:-1]:
         df['FileName_'+chan] = full_list_1
    temp_list = [[x] * seriesperwell for x in file_list_2]
    df['FileName_OrigPhalloidin'] = [x for sublist in temp_list for x in sublist]
    df['Frame_OrigPhalloidin'] = [0] * total_file_count
    df['Frame_OrigDNA'] = [0] * total_file_count
    df['Frame_OrigWGA'] = [1] * total_file_count
    df['Frame_OrigMito'] = [2] * total_file_count
    df['Frame_OrigER'] = [3] * total_file_count
    file_out_name = '/tmp/'+str(platename)+'.csv'
    df.to_csv(file_out_name,index=False)
    return file_out_name

def create_CSV_pipeline2(platename, seriesperwell, path, listoffiles):
    illum_path = path.replace('images','illum')
    columns = ['Metadata_Plate', 'Metadata_Series']
    columns_per_channel = ['PathName_','FileName_','Series_','Frame_']
    channels = ['Mito', 'DNA', 'ER', 'WGA', 'PhalloidinSlow','PhalloidinFast']
    columns += [col + chan for col in columns_per_channel for chan in channels]
    illum_columns_per_channel = ['PathName_Illum','FileName_Illum']
    illum_channels = ['Mito', 'DNA', 'ER', 'WGA', 'Phalloidin']
    columns += [col + chan for col in illum_columns_per_channel for chan in illum_channels]
    df = pandas.DataFrame(columns=columns)
    total_file_count = seriesperwell*len(listoffiles)
    df['Metadata_Plate'] = [platename] * total_file_count
    df['Metadata_Series'] = range(seriesperwell) * len(listoffiles)
    for chan in channels:
        df['Series_'+chan] = range(seriesperwell) * len(listoffiles)
        df['PathName_'+chan] = [path] * total_file_count
    file_list_1, file_list_2, file_list_3 = zip(*listoffiles)
    temp_list = [[x] * seriesperwell for x in file_list_3]
    full_list_1 = [x for sublist in temp_list for x in sublist]
    for chan in channels[:-2]:
         df['FileName_'+chan] = full_list_1
         df['FileName_Illum'+chan] = [platename+'_Illum'+chan] * total_file_count
         df['PathName_Illum'+chan] = [illum_path] * total_file_count
    temp_list = [[x] * seriesperwell for x in file_list_1]
    df['FileName_PhalloidinFast'] = [x for sublist in temp_list for x in sublist]
    temp_list = [[x] * seriesperwell for x in file_list_2]
    df['FileName_PhalloidinSlow'] = [x for sublist in temp_list for x in sublist]
    df['FileName_IllumPhalloidin'] = [platename+'_IllumPhalloidin'] * total_file_count
    df['PathName_IllumPhalloidin'] = [illum_path] * total_file_count
    df['Frame_PhalloidinFast'] = [0] * total_file_count
    df['Frame_PhalloidinSlow'] = [0] * total_file_count
    df['Frame_DNA'] = [0] * total_file_count
    df['Frame_WGA'] = [1] * total_file_count
    df['Frame_Mito'] = [2] * total_file_count
    df['Frame_ER'] = [3] * total_file_count
    file_out_name = '/tmp/'+str(platename)+'.csv'
    df.to_csv(file_out_name,index=False)
    return file_out_name
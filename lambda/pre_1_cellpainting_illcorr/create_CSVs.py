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

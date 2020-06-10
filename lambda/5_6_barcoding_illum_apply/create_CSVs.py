import pandas
import os

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

def create_CSV_pipeline2(platename, seriesperwell, path, illum_path,listoffiles, well_list):
    columns = ['Metadata_Plate', 'Metadata_Series', 'Metadata_Well', 'Metadata_Well_Value']
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
    well_df_list = []
    well_val_df_list = []
    for eachwell in well_list:
        well_df_list += [eachwell] * seriesperwell
        wellval = eachwell.split('Well')[1]
        if wellval[0] == '_':
            wellval = wellval[1:]
        well_val_df_list += [wellval] * seriesperwell
    df['Metadata_Well'] = well_df_list
    df['Metadata_Well_Value'] = well_val_df_list
    for chan in channels:
        df['Series_'+chan] = range(seriesperwell) * len(listoffiles)
        df['PathName_'+chan] = [path] * total_file_count
    file_list_1, file_list_2, file_list_3 = zip(*listoffiles)
    temp_list = [[x] * seriesperwell for x in file_list_3]
    full_list_1 = [x for sublist in temp_list for x in sublist]
    for chan in channels[:-2]:
         df['FileName_'+chan] = full_list_1
         df['FileName_Illum'+chan] = [platename+'_Illum'+chan+'.npy'] * total_file_count
         df['PathName_Illum'+chan] = [illum_path] * total_file_count
    temp_list = [[x] * seriesperwell for x in file_list_1]
    df['FileName_PhalloidinFast'] = [x for sublist in temp_list for x in sublist]
    temp_list = [[x] * seriesperwell for x in file_list_2]
    df['FileName_PhalloidinSlow'] = [x for sublist in temp_list for x in sublist]
    df['FileName_IllumPhalloidin'] = [platename+'_IllumPhalloidin.npy'] * total_file_count
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
    
def create_CSV_pipeline5(platename, seriesperwell, expected_cycles, path, platedict):
    expected_cycles = int(expected_cycles)
    columns = ['Metadata_Plate', 'Metadata_Series', 'Metadata_SBSCycle']
    columns_per_channel = ['PathName_','FileName_','Series_','Frame_']
    channels = ['OrigT', 'OrigG', 'OrigA', 'OrigC', 'OrigDNA']
    columns += [col + chan for col in columns_per_channel for chan in channels]
    df = pandas.DataFrame(columns=columns)
    well_list=platedict[1]
    total_file_count = seriesperwell * len(well_list) * expected_cycles
    df['Metadata_Plate'] = [platename] * total_file_count
    df['Metadata_Series'] = range(seriesperwell) * len(well_list) * expected_cycles
    cycle_list = []
    path_list = []
    A_list = []
    C_list = []
    G_list = []
    T_list = []
    DNA_list = []
    for cycle in range(1,(expected_cycles+1)):
        for eachwell in platedict[cycle]:
            cycle_list += [int(cycle)]*seriesperwell
            path_list += [os.path.join(path,platedict[cycle][eachwell][0])]*seriesperwell
            T_list += [platedict[cycle][eachwell][1][0]]*seriesperwell
            G_list += [platedict[cycle][eachwell][1][1]]*seriesperwell
            A_list += [platedict[cycle][eachwell][1][2]]*seriesperwell
            C_list += [platedict[cycle][eachwell][1][3]]*seriesperwell
            DNA_list += [platedict[cycle][eachwell][1][4]]*seriesperwell
    df['Metadata_SBSCycle'] = cycle_list
    for chan in channels:
        df['Series_'+chan] = range(seriesperwell) * len(well_list) * expected_cycles
        df['PathName_'+chan] = path_list
    df['FileName_OrigT'] = T_list
    df['FileName_OrigG'] = G_list
    df['FileName_OrigA'] = A_list
    df['FileName_OrigC'] = C_list
    df['FileName_OrigDNA'] = DNA_list
    df['Frame_OrigDNA'] = [0] * total_file_count
    df['Frame_OrigG'] = ([1]*seriesperwell*len(well_list))+([0]*seriesperwell*len(well_list)*(expected_cycles-1))
    df['Frame_OrigT'] = ([2]*seriesperwell*len(well_list))+([0]*seriesperwell*len(well_list)*(expected_cycles-1))
    df['Frame_OrigA'] = ([3]*seriesperwell*len(well_list))+([0]*seriesperwell*len(well_list)*(expected_cycles-1))
    df['Frame_OrigC'] = ([4]*seriesperwell*len(well_list))+([0]*seriesperwell*len(well_list)*(expected_cycles-1))
    file_out_name = '/tmp/'+str(platename)+'.csv'
    df.to_csv(file_out_name,index=False)
    return file_out_name
    
def create_CSV_pipeline6(platename, seriesperwell, expected_cycles, path, illum_path, platedict):
    expected_cycles = int(expected_cycles)
    columns = ['Metadata_Plate', 'Metadata_Series', 'Metadata_Well', 'Metadata_Well_Value']
    columns_per_channel = ['PathName_','FileName_','Series_','Frame_']
    cycles = ['Cycle%02d_' %x for x in range(1,expected_cycles+1)]
    or_il = ['Orig','Illum']
    channels = ['A','C','G','T', 'DNA']
    columns += [col+cycle+oi+channel for col in columns_per_channel for cycle in cycles for oi in or_il for channel in channels]
    df = pandas.DataFrame(columns=columns)
    well_list=platedict["1"].keys()
    total_file_count = seriesperwell * len(well_list)
    df['Metadata_Plate'] = [platename] * total_file_count
    df['Metadata_Series'] = range(seriesperwell) * len(well_list)
    well_df_list = []
    well_val_df_list = []
    for eachwell in well_list:
        well_df_list += [eachwell] * seriesperwell
        wellval = eachwell.split('Well')[1]
        if wellval[0] == '_':
            wellval = wellval[1:]
        well_val_df_list += [wellval] * seriesperwell
    df['Metadata_Well'] = well_df_list
    df['Metadata_Well_Value'] = well_val_df_list
    for cycle in range(1,(expected_cycles+1)):
        this_cycle = 'Cycle%02d_' % cycle
        path_list = []
        A_list = []
        C_list = []
        G_list = []
        T_list = []
        DNA_list = []
        for eachwell in platedict[str(cycle)]:
            path_list += [os.path.join(path,platedict[str(cycle)][eachwell][0])]*seriesperwell
            T_list += [platedict[str(cycle)][eachwell][1][0]]*seriesperwell
            G_list += [platedict[str(cycle)][eachwell][1][1]]*seriesperwell
            A_list += [platedict[str(cycle)][eachwell][1][2]]*seriesperwell
            C_list += [platedict[str(cycle)][eachwell][1][3]]*seriesperwell
            DNA_list += [platedict[str(cycle)][eachwell][1][4]]*seriesperwell
        for chan in channels:
            df['Series_'+this_cycle+'Orig'+chan] = range(seriesperwell) * len(well_list)
            df['PathName_'+this_cycle+'Orig'+chan] = path_list
            df['Series_'+this_cycle+'Illum'+chan] = df['Frame_'+this_cycle+'Illum'+chan] = [0] * total_file_count
            df['PathName_'+this_cycle+'Illum'+chan] = [illum_path] * total_file_count
            df['FileName_'+this_cycle+'Illum'+chan] = [platename +'_Cycle'+str(cycle)+'_Illum'+chan+'.npy'] * total_file_count #this name doesn't have digit padding
        df['FileName_'+this_cycle+'OrigT'] = T_list
        df['FileName_'+this_cycle+'OrigG'] = G_list
        df['FileName_'+this_cycle+'OrigA'] = A_list
        df['FileName_'+this_cycle+'OrigC'] = C_list
        df['FileName_'+this_cycle+'OrigDNA'] = DNA_list
        df['Frame_'+this_cycle+'OrigDNA'] = [0] * total_file_count
        if cycle == 1:
            df['Frame_'+this_cycle+'OrigG'] = [1] * total_file_count 
            df['Frame_'+this_cycle+'OrigT'] = [2] * total_file_count
            df['Frame_'+this_cycle+'OrigA'] = [3] * total_file_count
            df['Frame_'+this_cycle+'OrigC'] = [4] * total_file_count
        else:
            df['Frame_'+this_cycle+'OrigG'] = df['Frame_'+this_cycle+'OrigT'] = df['Frame_'+this_cycle+'OrigA'] = df['Frame_'+this_cycle+'OrigC'] = [0] * total_file_count
    file_out_name = '/tmp/'+str(platename)+'.csv'
    df.to_csv(file_out_name,index=False)
    return file_out_name
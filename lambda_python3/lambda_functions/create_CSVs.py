import pandas
import os
import ast

def create_CSV_pipeline1(platename, seriesperwell, path, listoffiles, one_or_many):
    columns = ["Metadata_Plate", "Metadata_Series"]
    if one_or_many == "one":
        columns_per_channel = ["PathName_", "FileName_", "Series_", "Frame_"]
        channels = ["OrigMito", "OrigDNA", "OrigER", "OrigWGA", "OrigPhalloidin"]
        columns += [col + chan for col in columns_per_channel for chan in channels]
        df = pandas.DataFrame(columns=columns)
        total_file_count = seriesperwell * len(listoffiles)
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Series"] = list(range(seriesperwell)) * len(listoffiles)
        file_list = [x[0] * seriesperwell for x in listoffiles]
        for chan in channels:
            df["Series_" + chan] = list(range(seriesperwell)) * len(listoffiles)
            df["PathName_" + chan] = [path] * total_file_count
            df["FileName_" + chan] = file_list
        df["Frame_OrigPhalloidin"] = [1] * total_file_count
        df["Frame_OrigDNA"] = [0] * total_file_count
        df["Frame_OrigWGA"] = [4] * total_file_count
        df["Frame_OrigMito"] = [2] * total_file_count
        df["Frame_OrigER"] = [3] * total_file_count
    else:
        columns_per_channel = ["PathName_", "FileName_", "Frame_"]
        channels = ["OrigMito", "OrigDNA", "OrigER", "OrigWGA", "OrigPhalloidin"]
        columns += [col + chan for col in columns_per_channel for chan in channels]
        df = pandas.DataFrame(columns=columns)
        total_file_count = seriesperwell * len(listoffiles)
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Series"] = list(range(seriesperwell)) * len(listoffiles)
        file_list = [x for well in listoffiles for x in well]
        for chan in channels:
            df["PathName_" + chan] = [path] * total_file_count
            df["FileName_" + chan] = file_list
        df["Frame_OrigPhalloidin"] = [1] * total_file_count
        df["Frame_OrigDNA"] = [0] * total_file_count
        df["Frame_OrigWGA"] = [4] * total_file_count
        df["Frame_OrigMito"] = [2] * total_file_count
        df["Frame_OrigER"] = [3] * total_file_count
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name

def create_CSV_pipeline1_SABER(platename, seriesperwell, path, platedict, one_or_many, SABERdict):
    if one_or_many == "one":
        print ("CSV creation not enabled for SABER for one file/well")
        return
    else:
        columns_per_channel = ["PathName_", "FileName_", "Frame_"]
        columns = ["Metadata_Plate", "Metadata_Series"]
        channels = []
        SABERdict = ast.literal_eval(SABERdict)
        rounddict = {}
        SABERrounds = list(SABERdict.keys())
        for eachround in SABERrounds:
            templist = []
            templist += SABERdict[eachround].values()
            channels += list(i[0] for i in templist)
            rounddict[eachround] = list(i[0] for i in templist)
        df = pandas.DataFrame(columns=columns)
        for chan in channels:
            listoffiles = []
            for round in rounddict.keys():
                if chan in rounddict[round]:
                    for well in platedict.keys():
                        listoffiles.append(platedict[well][round])
            listoffiles = [x for l in listoffiles for x in l]
            df["FileName_Orig" + chan] = listoffiles
        df["Metadata_Plate"] = [platename] * len(listoffiles)
        df["Metadata_Series"] = list(range(seriesperwell)) * len(platedict.keys())
        for eachround in SABERrounds:
            pathperround = path + eachround + '/'
            for chan in channels:
                for i in list(SABERdict[eachround].values()):
                    if chan == i[0]:
                        df["PathName_Orig" + chan] = pathperround
                        df["Frame_Orig" + chan] = i[1]
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name

def create_CSV_pipeline2(
    platename, seriesperwell, path, illum_path, listoffiles, well_list, one_or_many
):
    columns = [
        "Metadata_Plate",
        "Metadata_Site",
        "Metadata_Well",
        "Metadata_Well_Value",
    ]
    if one_or_many == "one":
        columns_per_channel = [
            "PathName_",
            "FileName_",
            "Series_",
            "Frame_",
            "PathName_Illum",
            "FileName_Illum",
        ]
        channels = ["Mito", "DNA", "ER", "WGA", "Phalloidin"]
        columns += [col + chan for col in columns_per_channel for chan in channels]
        df = pandas.DataFrame(columns=columns)
        total_file_count = seriesperwell * len(listoffiles)
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Site"] = list(range(seriesperwell)) * len(listoffiles)
        well_df_list = []
        well_val_df_list = []
        for eachwell in well_list:
            well_df_list += [eachwell] * seriesperwell
            wellval = eachwell.split("Well")[1]
            if wellval[0] == "_":
                wellval = wellval[1:]
            well_val_df_list += [wellval] * seriesperwell
        df["Metadata_Well"] = well_df_list
        df["Metadata_Well_Value"] = well_val_df_list
        file_list = [x[0] * seriesperwell for x in listoffiles]
        for chan in channels:
            df["Series_" + chan] = list(range(seriesperwell)) * len(listoffiles)
            df["PathName_" + chan] = [path] * total_file_count
            df["FileName_" + chan] = file_list
            df["FileName_Illum" + chan] = [
                platename + "_Illum" + chan + ".npy"
            ] * total_file_count
            df["PathName_Illum" + chan] = [illum_path] * total_file_count
        df["Frame_DNA"] = [0] * total_file_count
        df["Frame_WGA"] = [4] * total_file_count
        df["Frame_Mito"] = [2] * total_file_count
        df["Frame_ER"] = [3] * total_file_count
        df["Frame_Phalloidin"] = [1] * total_file_count
    else:
        columns_per_channel = [
            "PathName_",
            "FileName_",
            "Frame_",
            "PathName_Illum",
            "FileName_Illum",
        ]
        channels = ["Mito", "DNA", "ER", "WGA", "Phalloidin"]
        columns += [col + chan for col in columns_per_channel for chan in channels]
        df = pandas.DataFrame(columns=columns)
        total_file_count = seriesperwell * len(listoffiles)
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Site"] = list(range(seriesperwell)) * len(listoffiles)
        well_df_list = []
        well_val_df_list = []
        for eachwell in well_list:
            well_df_list += [eachwell] * seriesperwell
            wellval = eachwell.split("Well")[1]
            if wellval[0] == "_":
                wellval = wellval[1:]
            well_val_df_list += [wellval] * seriesperwell
        df["Metadata_Well"] = well_df_list
        df["Metadata_Well_Value"] = well_val_df_list
        file_list = [x for well in listoffiles for x in well]
        for chan in channels:
            df["PathName_" + chan] = [path] * total_file_count
            df["FileName_" + chan] = file_list
            df["FileName_Illum" + chan] = [
                platename + "_Illum" + chan + ".npy"
            ] * total_file_count
            df["PathName_Illum" + chan] = [illum_path] * total_file_count
        df["Frame_DNA"] = [0] * total_file_count
        df["Frame_WGA"] = [4] * total_file_count
        df["Frame_Mito"] = [2] * total_file_count
        df["Frame_ER"] = [3] * total_file_count
        df["Frame_Phalloidin"] = [1] * total_file_count
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name


def create_CSV_pipeline3(platename, seriesperwell, path, well_list, range_skip):
    columns = [
        "Metadata_Plate",
        "Metadata_Site",
        "Metadata_Well",
        "Metadata_Well_Value",
    ]
    columns_per_channel = ["PathName_", "FileName_"]
    channels = ["DNA", "Phalloidin"]
    columns += [col + chan for col in columns_per_channel for chan in channels]
    df = pandas.DataFrame(columns=columns)
    sitelist = list(range(0, seriesperwell, range_skip))
    sites_per_well = len(sitelist)
    total_file_count = sites_per_well * len(well_list)
    df["Metadata_Plate"] = [platename] * total_file_count
    df["Metadata_Site"] = sitelist * len(well_list)
    well_df_list = []
    well_val_df_list = []
    parsed_well_list = []
    for eachwell in well_list:
        well_df_list += [eachwell] * sites_per_well
        wellval = eachwell.split("Well")[1]
        if wellval[0] == "_":
            wellval = wellval[1:]
        well_val_df_list += [wellval] * sites_per_well
        parsed_well_list.append(wellval)
    df["Metadata_Well"] = well_df_list
    df["Metadata_Well_Value"] = well_val_df_list
    path_list = [
        os.path.join(path, platename + "-" + well)
        for well in well_list
        for site in sitelist
    ]
    for chan in channels:
        df["PathName_" + chan] = path_list
        df["FileName_" + chan] = [
            "Plate_"
            + platename
            + "_Well_"
            + well
            + "_Site_"
            + str(site)
            + "_Corr"
            + chan
            + ".tiff"
            for well in parsed_well_list
            for site in sitelist
        ]
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name


def create_CSV_pipeline5(
    platename,
    seriesperwell,
    expected_cycles,
    path,
    platedict,
    one_or_many,
    fast_or_slow,
):
    expected_cycles = int(expected_cycles)
    columns = ["Metadata_Plate", "Metadata_Site", "Metadata_SBSCycle"]
    channels = ["OrigT", "OrigG", "OrigA", "OrigC", "OrigDNA"]
    if one_or_many == "one" and fast_or_slow == "fast":
        columns_per_channel = ["PathName_", "FileName_", "Series_", "Frame_"]
        columns += [col + chan for col in columns_per_channel for chan in channels]
        df = pandas.DataFrame(columns=columns)
        well_list = platedict[1]
        total_file_count = seriesperwell * len(well_list) * expected_cycles
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Site"] = (
            list(range(seriesperwell)) * len(well_list) * expected_cycles
        )
        cycle_list = []
        path_list = []
        A_list = []
        C_list = []
        G_list = []
        T_list = []
        DNA_list = []
        for cycle in range(1, (expected_cycles + 1)):
            for eachwell in platedict[cycle]:
                cycle_list += [int(cycle)] * seriesperwell
                path_list += [
                    os.path.join(path, platedict[cycle][eachwell][0])
                ] * seriesperwell
                T_list += [platedict[cycle][eachwell][1][0]] * seriesperwell
                G_list += [platedict[cycle][eachwell][1][1]] * seriesperwell
                A_list += [platedict[cycle][eachwell][1][2]] * seriesperwell
                C_list += [platedict[cycle][eachwell][1][3]] * seriesperwell
                DNA_list += [platedict[cycle][eachwell][1][4]] * seriesperwell
        df["Metadata_SBSCycle"] = cycle_list
        for chan in channels:
            df["Series_" + chan] = (
                list(range(seriesperwell)) * len(well_list) * expected_cycles
            )
            df["PathName_" + chan] = path_list
        df["FileName_OrigT"] = T_list
        df["FileName_OrigG"] = G_list
        df["FileName_OrigA"] = A_list
        df["FileName_OrigC"] = C_list
        df["FileName_OrigDNA"] = DNA_list
        df["Frame_OrigDNA"] = [0] * total_file_count
        df["Frame_OrigG"] = ([1] * seriesperwell * len(well_list)) + (
            [0] * seriesperwell * len(well_list) * (expected_cycles - 1)
        )
        df["Frame_OrigT"] = ([2] * seriesperwell * len(well_list)) + (
            [0] * seriesperwell * len(well_list) * (expected_cycles - 1)
        )
        df["Frame_OrigA"] = ([3] * seriesperwell * len(well_list)) + (
            [0] * seriesperwell * len(well_list) * (expected_cycles - 1)
        )
        df["Frame_OrigC"] = ([4] * seriesperwell * len(well_list)) + (
            [0] * seriesperwell * len(well_list) * (expected_cycles - 1)
        )
    elif one_or_many == "many" and fast_or_slow == "slow":
        columns_per_channel = ["PathName_", "FileName_", "Frame_"]
        columns += [col + chan for col in columns_per_channel for chan in channels]
        df = pandas.DataFrame(columns=columns)
        well_list = platedict[1]
        total_file_count = seriesperwell * len(well_list) * expected_cycles
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Site"] = (
            list(range(seriesperwell)) * len(well_list) * expected_cycles
        )
        cycle_list = []
        path_list = []
        file_list = []
        for cycle in range(1, (expected_cycles + 1)):
            for eachwell in platedict[cycle]:
                cycle_list += [int(cycle)] * seriesperwell
                path_list += [
                    os.path.join(path, platedict[cycle][eachwell][0])
                ] * seriesperwell
                file_list += platedict[cycle][eachwell][1]
        df["Metadata_SBSCycle"] = cycle_list
        for chan in channels:
            df["PathName_" + chan] = path_list
            df["FileName_" + chan] = file_list
        df["Frame_OrigDNA"] = [0] * total_file_count
        df["Frame_OrigG"] = [1] * total_file_count
        df["Frame_OrigT"] = [2] * total_file_count
        df["Frame_OrigA"] = [3] * total_file_count
        df["Frame_OrigC"] = [4] * total_file_count
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name


def create_CSV_pipeline6(
    platename,
    seriesperwell,
    expected_cycles,
    path,
    illum_path,
    platedict,
    one_or_many,
    fast_or_slow,
):
    expected_cycles = int(expected_cycles)
    if one_or_many == "one" and fast_or_slow == "fast":
        columns = [
            "Metadata_Plate",
            "Metadata_Series",
            "Metadata_Well",
            "Metadata_Well_Value",
            "Metadata_ArbitraryGroup",
        ]
        columns_per_channel = ["PathName_", "FileName_", "Series_", "Frame_"]
        cycles = ["Cycle%02d_" % x for x in range(1, expected_cycles + 1)]
        or_il = ["Orig", "Illum"]
        channels = ["A", "C", "G", "T", "DNA"]
        columns += [
            col + cycle + oi + channel
            for col in columns_per_channel
            for cycle in cycles
            for oi in or_il
            for channel in channels
        ]
        df = pandas.DataFrame(columns=columns)
        well_list = list(platedict["1"].keys())
        total_file_count = seriesperwell * len(well_list)
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Series"] = list(range(seriesperwell)) * len(well_list)
        df["Metadata_ArbitraryGroup"] = list(range(19)) * 19 * len(well_list)
        well_df_list = []
        well_val_df_list = []
        for eachwell in well_list:
            well_df_list += [eachwell] * seriesperwell
            wellval = eachwell.split("Well")[1]
            if wellval[0] == "_":
                wellval = wellval[1:]
            well_val_df_list += [wellval] * seriesperwell
        df["Metadata_Well"] = well_df_list
        df["Metadata_Well_Value"] = well_val_df_list
        for cycle in range(1, (expected_cycles + 1)):
            this_cycle = "Cycle%02d_" % cycle
            path_list = []
            A_list = []
            C_list = []
            G_list = []
            T_list = []
            DNA_list = []
            for eachwell in platedict[str(cycle)]:
                path_list += [
                    os.path.join(path, platedict[str(cycle)][eachwell][0])
                ] * seriesperwell
                T_list += [platedict[str(cycle)][eachwell][1][0]] * seriesperwell
                G_list += [platedict[str(cycle)][eachwell][1][1]] * seriesperwell
                A_list += [platedict[str(cycle)][eachwell][1][2]] * seriesperwell
                C_list += [platedict[str(cycle)][eachwell][1][3]] * seriesperwell
                DNA_list += [platedict[str(cycle)][eachwell][1][4]] * seriesperwell
            for chan in channels:
                df["Series_" + this_cycle + "Orig" + chan] = list(range(seriesperwell)) * len(
                    well_list
                )
                df["PathName_" + this_cycle + "Orig" + chan] = path_list
                df["Series_" + this_cycle + "Illum" + chan] = df[
                    "Frame_" + this_cycle + "Illum" + chan
                ] = [0] * total_file_count
                df["PathName_" + this_cycle + "Illum" + chan] = [
                    illum_path
                ] * total_file_count
                df["FileName_" + this_cycle + "Illum" + chan] = [
                    platename + "_Cycle" + str(cycle) + "_Illum" + chan + ".npy"
                ] * total_file_count  # this name doesn't have digit padding
            df["FileName_" + this_cycle + "OrigT"] = T_list
            df["FileName_" + this_cycle + "OrigG"] = G_list
            df["FileName_" + this_cycle + "OrigA"] = A_list
            df["FileName_" + this_cycle + "OrigC"] = C_list
            df["FileName_" + this_cycle + "OrigDNA"] = DNA_list
            df["Frame_" + this_cycle + "OrigDNA"] = [0] * total_file_count
            if cycle == 1:
                df["Frame_" + this_cycle + "OrigG"] = [1] * total_file_count
                df["Frame_" + this_cycle + "OrigT"] = [2] * total_file_count
                df["Frame_" + this_cycle + "OrigA"] = [3] * total_file_count
                df["Frame_" + this_cycle + "OrigC"] = [4] * total_file_count
            else:
                df["Frame_" + this_cycle + "OrigG"] = df[
                    "Frame_" + this_cycle + "OrigT"
                ] = df["Frame_" + this_cycle + "OrigA"] = df[
                    "Frame_" + this_cycle + "OrigC"
                ] = (
                    [0] * total_file_count
                )
    elif one_or_many == "many" and fast_or_slow == "slow":
        columns = [
            "Metadata_Plate",
            "Metadata_Site",
            "Metadata_Well",
            "Metadata_Well_Value",
        ]
        columns_per_channel = ["PathName_", "FileName_", "Frame_"]
        cycles = ["Cycle%02d_" % x for x in range(1, expected_cycles + 1)]
        or_il = ["Orig", "Illum"]
        channels = ["A", "C", "G", "T", "DNA"]
        columns += [
            col + cycle + oi + channel
            for col in columns_per_channel
            for cycle in cycles
            for oi in or_il
            for channel in channels
        ]
        df = pandas.DataFrame(columns=columns)
        well_list = list(platedict["1"].keys())
        total_file_count = seriesperwell * len(well_list)
        df["Metadata_Plate"] = [platename] * total_file_count
        df["Metadata_Site"] = list(range(seriesperwell)) * len(well_list)
        well_df_list = []
        well_val_df_list = []
        for eachwell in well_list:
            well_df_list += [eachwell] * seriesperwell
            wellval = eachwell.split("Well")[1]
            if wellval[0] == "_":
                wellval = wellval[1:]
            well_val_df_list += [wellval] * seriesperwell
        df["Metadata_Well"] = well_df_list
        df["Metadata_Well_Value"] = well_val_df_list
        for cycle in range(1, (expected_cycles + 1)):
            this_cycle = "Cycle%02d_" % cycle
            path_list = []
            file_list = []
            for eachwell in platedict[str(cycle)]:
                path_list += [
                    os.path.join(path, platedict[str(cycle)][eachwell][0])
                ] * seriesperwell
                file_list += platedict[str(cycle)][eachwell][1]
            for chan in channels:
                df["PathName_" + this_cycle + "Orig" + chan] = path_list
                df["Frame_" + this_cycle + "Illum" + chan] = [0] * total_file_count
                df["PathName_" + this_cycle + "Illum" + chan] = [
                    illum_path
                ] * total_file_count
                df["FileName_" + this_cycle + "Illum" + chan] = [
                    platename + "_Cycle" + str(cycle) + "_Illum" + chan + ".npy"
                ] * total_file_count  # this name doesn't have digit padding
                df["FileName_" + this_cycle + "Orig" + chan] = file_list
            df["Frame_" + this_cycle + "OrigDNA"] = [0] * total_file_count
            df["Frame_" + this_cycle + "OrigG"] = [1] * total_file_count
            df["Frame_" + this_cycle + "OrigT"] = [2] * total_file_count
            df["Frame_" + this_cycle + "OrigA"] = [3] * total_file_count
            df["Frame_" + this_cycle + "OrigC"] = [4] * total_file_count
        file_out_name = "/tmp/" + str(platename) + ".csv"
        df.to_csv(file_out_name, index=False)
        return file_out_name


def create_CSV_pipeline7(platename, seriesperwell, expected_cycles, path, well_list):
    expected_cycles = int(expected_cycles)
    columns = [
        "Metadata_Plate",
        "Metadata_Site",
        "Metadata_Well",
        "Metadata_Well_Value",
    ]
    columns_per_channel = ["PathName_", "FileName_"]
    cycles = ["Cycle%02d_" % x for x in range(1, expected_cycles + 1)]
    channels = ["A", "C", "G", "T"]
    columns += [
        col + cycle + channel
        for col in columns_per_channel
        for cycle in cycles
        for channel in channels
    ]
    columns += ["PathName_Cycle01_DAPI", "FileName_Cycle01_DAPI"]
    df = pandas.DataFrame(columns=columns)
    total_file_count = seriesperwell * len(well_list)
    df["Metadata_Plate"] = [platename] * total_file_count
    df["Metadata_Site"] = list(range(seriesperwell)) * len(well_list)
    well_df_list = []
    well_val_df_list = []
    parsed_well_list = []
    pathlist = []
    for eachwell in well_list:
        well_df_list += [eachwell] * seriesperwell
        pathlist += [os.path.join(path, platename + "-" + eachwell)] * seriesperwell
        if "Well" not in eachwell:
            well_val = eachwell
        else:
            if "Well_" in eachwell:
                well_val = eachwell[5:]
            else:
                well_val = eachwell[4:]
        parsed_well_list.append(well_val)
        well_val_df_list += [well_val] * seriesperwell
    df["Metadata_Well"] = well_df_list
    df["Metadata_Well_Value"] = well_val_df_list
    for cycle in range(1, (expected_cycles + 1)):
        this_cycle = "_Cycle%02d_" % cycle
        for chan in channels:
            df["PathName" + this_cycle + chan] = pathlist
            df["FileName" + this_cycle + chan] = [
                "Plate_"
                + platename
                + "_Well_"
                + well
                + "_Site_"
                + str(site)
                + this_cycle
                + chan
                + ".tiff"
                for well in parsed_well_list
                for site in range(seriesperwell)
            ]  # this name doesn't have digit padding
        if cycle == 1:
            df["PathName_Cycle01_DAPI"] = pathlist
            df["FileName_Cycle01_DAPI"] = [
                "Plate_"
                + platename
                + "_Well_"
                + well
                + "_Site_"
                + str(site)
                + "_Cycle01_DAPI.tiff"
                for well in parsed_well_list
                for site in range(seriesperwell)
            ]
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name


def create_CSV_pipeline9(platename, numsites, expected_cycles, path, well_list):
    expected_cycles = int(expected_cycles)
    columns = [
        "Metadata_Plate",
        "Metadata_Site",
        "Metadata_Well",
        "Metadata_Well_Value",
    ]
    columns_per_channel = ["PathName_", "FileName_"]
    cycles = ["Cycle%02d_" % x for x in range(1, expected_cycles + 1)]
    channels = ["A", "C", "G", "T"]
    columns += [
        col + cycle + channel
        for col in columns_per_channel
        for cycle in cycles
        for channel in channels
    ]
    columns += ["PathName_Cycle01_DAPI", "FileName_Cycle01_DAPI"]
    cp_columns = ["CorrDNA", "CorrER", "CorrMito", "CorrPhalloidin", "CorrWGA"]
    columns += [
        prefix + suffix for prefix in columns_per_channel for suffix in cp_columns
    ]
    df = pandas.DataFrame(columns=columns)
    total_file_count = numsites * len(well_list)
    df["Metadata_Plate"] = [platename] * total_file_count
    df["Metadata_Site"] = list(range(1, numsites + 1)) * len(
        well_list
    )  # tile counting starts at 1 not 0
    pathlist = []
    namesuflist = []
    for well in well_list:
        for site in range(1, numsites + 1):
            pathlist.append(path + "/" + platename + "_" + well + "/")
            namesuflist.append("_Site_" + str(site) + ".tiff")
    for col in cp_columns:
        pathnamelist = [path + col for path in pathlist]
        df["PathName_" + col] = pathnamelist
        namelist = [col + name for name in namesuflist]
        df["FileName_" + col] = namelist
    well_df_list = []
    well_val_df_list = []
    parsed_well_list = []
    pathlist = []
    for eachwell in well_list:
        well_df_list += [eachwell] * numsites
        pathlist += [os.path.join(path, platename + "_" + eachwell)] * numsites
        if "Well" not in eachwell:
            well_val = eachwell
        else:
            if "Well_" in eachwell:
                well_val = eachwell[5:]
            else:
                well_val = eachwell[4:]
        parsed_well_list.append(well_val)
        well_val_df_list += [well_val] * numsites
    df["Metadata_Well"] = well_df_list
    df["Metadata_Well_Value"] = well_val_df_list
    for cycle in range(1, (expected_cycles + 1)):
        this_cycle = "Cycle%02d" % cycle
        pathcycle = "/Cycle%02d_" % cycle
        for chan in channels:
            pathnamelist = [path + pathcycle + chan for path in pathlist]
            df["PathName_" + this_cycle + "_" + chan] = pathnamelist
            df["FileName_" + this_cycle + "_" + chan] = [
                this_cycle
                + "_"
                + chan
                + "_Site_"
                + str(site)
                + ".tiff"
                for well in parsed_well_list
                for site in range(1, numsites + 1)
            ]  # this name doesn't have digit padding
        if cycle == 1:
            pathnamelist = [path + "/Cycle01_DAPI" for path in pathlist]
            df["PathName_Cycle01_DAPI"] = pathnamelist
            df["FileName_Cycle01_DAPI"] = [
                "Cycle01_DAPI_Site_"
                + str(site)
                + ".tiff"
                for well in parsed_well_list
                for site in range(1, numsites + 1)
            ]
    file_out_name = "/tmp/" + str(platename) + ".csv"
    df.to_csv(file_out_name, index=False)
    return file_out_name

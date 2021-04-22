#@String input_file_location
#@String subdir
#@String out_subdir_tag
#@String rows
#@String columns
#@String imperwell
#@String stitchorder
#@String channame
#@String size
#@String overlap_pct
#@String tileperside
#@String filterstring
#@String scalingstring
#@String awsdownload
#@String bucketname
#@String localtemp
#@String downloadfilter
#@String round_or_square
#@String final_tile_size
#@String xoffset_tiles
#@String yoffset_tiles
#@String compress

from ij import IJ, WindowManager
import os
import string
import sys
import time

from loci.plugins.out import Exporter
from loci.plugins import LociExporter
plugin = LociExporter()

def tiffextend(imname):
        if '.tif' in imname:
                return imname
        if '.' in imname:
                return imname[:imname.index('.')]+'.tiff'
        else:
                return imname+'.tiff'

def savefile(im,imname,plugin,compress='false'):
        attemptcount = 0
        imname = tiffextend(imname)
        print('Saving ',imname,im.width,im.height)
        if compress.lower()!='true':
                IJ.saveAs(im, "tiff",imname)
        else:
                while attemptcount <5:
                        try:
                                plugin.arg="outfile="+imname+" windowless=true compression=LZW saveROI=false"
                                exporter = Exporter(plugin, im)
                                exporter.run()
                                print('Succeeded after attempt ',attemptcount)
                                return
                        except:
                                attemptcount +=1
                print('failed 5 times at saving')

top_outfolder = 'output'

if not os.path.exists(top_outfolder):
        os.mkdir(top_outfolder)

# Define and create the parent folders where the images will be output
outfolder=os.path.join(top_outfolder,'images_corrected_stitched')
tile_outdir = os.path.join(top_outfolder,'images_corrected_cropped')
downsample_outdir = os.path.join(top_outfolder,'images_corrected_stitched_10X')
if not os.path.exists(outfolder):
        os.mkdir(outfolder)
if not os.path.exists(tile_outdir):
        os.mkdir(tile_outdir)
if not os.path.exists(downsample_outdir):
        os.mkdir(downsample_outdir)

# Define and create the batch-specific subfolders where the images will be output
out_subdir=os.path.join(outfolder, out_subdir_tag)
tile_subdir=os.path.join(tile_outdir, out_subdir_tag)
downsample_subdir=os.path.join(downsample_outdir, out_subdir_tag)
if not os.path.exists(tile_subdir):
        os.mkdir(tile_subdir)
if not os.path.exists(downsample_subdir):
        os.mkdir(downsample_subdir)
if not os.path.exists(out_subdir):
        os.mkdir(out_subdir)

subdir=os.path.join(input_file_location,subdir)

if awsdownload == 'True':
        if not os.path.exists(localtemp):
                os.mkdir(localtemp)
        import subprocess
        cmd = ['aws','s3','sync','--exclude', '*', '--include', str(downloadfilter)]
        cmd += ['s3://'+str(bucketname)+'/'+ str(subdir).split('ubuntu/bucket/')[1], str(localtemp)]
        print('Running', cmd)
        subp = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
                output= subp.stdout.readline()
                if output== '' and subp.poll() is not None:
                        break
                if output:
                        print(output.strip())
        # Examine all downloaded files and make a list of the tifs
        tiflist=[]
        for root, dirs, files in os.walk(localtemp):
                for name in files:
                        if '.tif' in name:
                                if 'Overlay' not in name:
                                        tiflist.append([root,name])
        print(len(tiflist), 'tifs found')
        for eachtif in tiflist:
                # If the tif is in a subfolder
                if eachtif[0]!=localtemp:
                        os.rename(os.path.join(eachtif[0],eachtif[1]),os.path.join(localtemp,eachtif[1]))
                        print ("Successfully moved", os.path.join(localtemp,eachtif[1]))
        subdir = localtemp


if os.path.isdir(subdir):
        dirlist=os.listdir(subdir)
        welllist=[]
        presuflist = []
        permprefix = None
        permsuffix = None
        for eachfile in dirlist:
                        if '.tif' in eachfile:
                                if filterstring in eachfile:
                                        if 'Overlay' not in eachfile:
                                                prefixBeforeWell,suffixWithWell=eachfile.split('_Well_')
                                                Well,suffixAfterWell=suffixWithWell.split('_Site_')
                                                channelSuffix = suffixAfterWell[suffixAfterWell.index('_')+1:]
                                                if (prefixBeforeWell,channelSuffix) not in presuflist:
                                                        presuflist.append((prefixBeforeWell,channelSuffix))
                                                if Well not in welllist:
                                                        welllist.append(Well)
                                                if channame in channelSuffix:
                                                        if permprefix == None:
                                                                permprefix=prefixBeforeWell
                                                                permsuffix=channelSuffix

        for eachpresuf in presuflist:
                if eachpresuf[1][-4:]!='.tif':
                        if eachpresuf[1][-5:]!='.tiff':
                                presuflist.remove(eachpresuf)
        presuflist.sort()
        print welllist, presuflist

        if round_or_square == 'square':
                stitchedsize=int(rows)*int(size)
                tileperside=int(tileperside)
                scale_factor=float(scalingstring)
                rounded_scale_factor=int(round(scale_factor))
                upscaledsize=int(stitchedsize*rounded_scale_factor)
                if upscaledsize > 46340:
                        upscaledsize = 46340
                tilesize=int(upscaledsize/tileperside)

                for eachwell in welllist:
                        standard_grid_instructions=["type=["+stitchorder+"] order=[Right & Down                ] grid_size_x="+rows+" grid_size_y="+columns+" tile_overlap="+overlap_pct+" first_file_index_i=0 directory="+subdir+" file_names=",
                        " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                        copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                        filename=permprefix+'_Well_'+eachwell+'_Site_{i}_'+permsuffix
                        fileoutname='Stitched'+filename.replace("{i}","")
                        IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                        im=IJ.getImage()
                        #We're going to overwrite this file later, but it gives is a chance for an early checkpoint
                        #This doesn't seem to play nicely with the compression option on, it doesn't get overwritten later and bad things happen
                        if compress.lower()!='true':
                                savefile(im,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                        IJ.run("Close All")
                        for eachpresuf in presuflist:
                                thisprefix, thissuffix=eachpresuf
                                thissuffixnicename = thissuffix.split('.')[0]
                                if thissuffixnicename[0]=='_':
                                        thissuffixnicename=thissuffixnicename[1:]
                                tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)
                                if not os.path.exists(tile_subdir_persuf):
                                        os.mkdir(tile_subdir_persuf)
                                filename=thisprefix+'_Well_'+eachwell+'_Site_{i}_'+thissuffix
                                fileoutname='Stitched'+filename.replace("{i}","")
                                with open(os.path.join(subdir, 'TileConfiguration.registered.txt'),'r') as infile:
                                        with open(os.path.join(subdir, 'TileConfiguration.registered_copy.txt'),'w') as outfile:
                                                for line in infile:
                                                        line=line.replace(permprefix,thisprefix)
                                                        line=line.replace(permsuffix,thissuffix)
                                                        outfile.write(line)

                                IJ.run("Grid/Collection stitching", copy_grid_instructions)
                                im=IJ.getImage()
                                width = str(int(round(im.width*float(scalingstring))))
                                height = str(int(round(im.height*float(scalingstring))))
                                print("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                time.sleep(15)
                                im2=IJ.getImage()
                                print("Canvas Size...", "width="+str(upscaledsize)+" height="+str(upscaledsize)+" position=Top-Left zero")
                                IJ.run("Canvas Size...", "width="+str(upscaledsize)+" height="+str(upscaledsize)+" position=Top-Left zero")
                                time.sleep(15)
                                im3=IJ.getImage()
                                savefile(im3,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                                im=IJ.getImage()
                                print("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.run("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.getImage()
                                savefile(im_10,os.path.join(downsample_subdir,fileoutname),plugin,compress=compress)
                                IJ.run("Close All")
                                im=IJ.open(os.path.join(out_subdir,fileoutname))
                                im = IJ.getImage()
                                for eachxtile in range(tileperside):
                                        for eachytile in range(tileperside):
                                                each_tile_num = eachxtile*tileperside + eachytile + 1
                                                IJ.makeRectangle(eachxtile*tilesize, eachytile*tilesize,tilesize,tilesize)
                                                im_tile=im.crop()
                                                savefile(im_tile,os.path.join(tile_subdir_persuf,thissuffixnicename+'_Site_'+str(each_tile_num)+'.tiff'),plugin,compress=compress)
                                IJ.run("Close All")
        elif round_or_square == 'round':
                if imperwell == '1364':
                        row_widths = [8,14,18,22,26,28,30,
                        32,34,34,36,36,38,38,
                        40,40,40,42,42,42,42,
                        42,42,42,42,40,40,40,
                        38,38,36,36,34,34,32,
                        30,28,26,22,18,14,8]
                elif imperwell == '1332':
                        row_widths = [14,18,22,26,28,30,
                        32,34,34,36,36,38,38,
                        40,40,40,40,40,40,40,
                        40,40,40,40,40,40,40,
                        38,38,36,36,34,34,32,
                        30,28,26,22,18,14]
                elif imperwell == '320':
                        row_widths = [4, 8, 12, 14, 16,
                        18, 18, 20, 20, 20,
                        20, 20, 20, 20, 18,
                        18, 16, 14, 12, 8, 4]
                elif imperwell == '316':
                        row_widths = [6, 10, 14, 16, 16,
                        18, 18, 20, 20, 20,
                        20, 20, 20, 18, 18,
                        16, 16, 14, 10, 6]
                else:
                        print(imperwell, "images/well for a round well is not currently supported")
                        sys.exit()

                rows = str(len(row_widths))
                columns = str(max(row_widths))

                # xoffset_tiles and yoffset_tiles can be used if you need to adjust the "where to draw the line between quarters"
                # by a whole tile. You may want to add more padding if you do this
                top_rows = str((int(rows)/2)+int(yoffset_tiles))
                left_columns = str((int(columns)/2)+int(xoffset_tiles))
                bot_rows = str(int(rows)-int(top_rows))
                right_columns = str(int(columns)-int(left_columns))
                scale_factor=float(scalingstring)
                rounded_scale_factor=int(round(scale_factor))
                #For upscaled row and column size, we're always going to use the biggest number, we'd rather pad than miss stuff
                #Because we can't assure same final tile size now either, now we need to specify it, ugh, and make sure the padding is big enough
                max_val = max(int(top_rows),int(bot_rows),int(left_columns),int(right_columns))
                upscaled_row_size=int(size)*max_val*rounded_scale_factor
                tiles_per_quarter = int(tileperside)/2
                tilesize=int(final_tile_size)
                if tilesize * tiles_per_quarter > upscaled_row_size:
                        upscaled_row_size = tilesize * tiles_per_quarter
                upscaled_col_size=upscaled_row_size
                pixels_to_crop = int(round(int(size)*float(overlap_pct)/200))

                pos_dict = {}
                count = 0
                for row in range(len(row_widths)):
                        row_width = row_widths[row]
                        left_pos = int((int(columns)-row_width)/2)
                        for col in range(row_width):
                                if row%2 == 0:
                                        pos_dict[(int(left_pos + col), row)] = str(count)
                                        count += 1
                                else:
                                        right_pos = left_pos + row_width - 1
                                        pos_dict[(int(right_pos - col), row)]= str(count)
                                        count += 1

                filled_positions = pos_dict.keys()
                for eachwell in welllist:
                        for eachpresuf in presuflist:
                                thisprefix, thissuffix=eachpresuf
                                for x in range(int(columns)):
                                        for y in range(int(rows)):
                                                out_name = thisprefix+'_Well_'+eachwell+'_x_'+ '%02d'%x+'_y_'+'%02d'%y+ '_'+ thissuffix
                                                if (x,y) in filled_positions:
                                                        series = pos_dict[(x,y)]
                                                        in_name = thisprefix+'_Well_'+eachwell+'_Site_'+str(series)+'_'+thissuffix
                                                        IJ.open(os.path.join(subdir,in_name))
                                                else:
                                                        IJ.newImage("Untitled", "16-bit noise",int(size),int(size), 1)
                                                        IJ.run("Divide...", "value=300") #get the noise value below the real camera noise level
                                                im = IJ.getImage()
                                                IJ.saveAs(im,'tiff',os.path.join(subdir, out_name))
                                                IJ.run("Close All")
                                                if (x,y) in filled_positions:
                                                        try: #try to clean up after yourself, but don't die if you can't
                                                                os.remove(os.path.join(subdir,in_name))
                                                        except:
                                                                pass
                                print("Renamed all files for prefix "+thisprefix+" and suffix "+thissuffix+" in well "+eachwell)
                        imagelist = os.listdir(subdir)
                        print(len(imagelist), 'files in subdir')
                        print(imagelist[:10])
                        #top left quarter
                        print('Running top left')
                        #Change per quarter
                        standard_grid_instructions=["type=[Filename defined position] order=[Defined by filename         ] grid_size_x="+str(left_columns)+" grid_size_y="+top_rows+" tile_overlap="+overlap_pct+" first_file_index_x=0 first_file_index_y=0 directory="+subdir+" file_names=",
                        " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                        copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                        filename=permprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+permsuffix
                        #Change per quarter
                        fileoutname='StitchedTopLeft'+filename.replace("{xx}","").replace("{yy}","")
                        instructions = standard_grid_instructions[0] + filename + standard_grid_instructions[1]
                        print(instructions)
                        IJ.run("Grid/Collection stitching", instructions)
                        im=IJ.getImage()
                        #We're going to overwrite this file later, but it gives us a chance for an early checkpoint
                        #This doesn't seem to play nicely with the compression option on, it doesn't get overwritten later and bad things happen
                        if compress.lower()!='true':
                                savefile(im,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                        IJ.run("Close All")
                        for eachpresuf in presuflist:
                                thisprefix, thissuffix=eachpresuf
                                thissuffixnicename = thissuffix.split('.')[0]
                                if thissuffixnicename[0]=='_':
                                        thissuffixnicename=thissuffixnicename[1:]
                                tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)
                                if not os.path.exists(tile_subdir_persuf):
                                        os.mkdir(tile_subdir_persuf)
                                filename=thisprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+thissuffix
                                #Change per quarter
                                fileoutname='StitchedTopLeft'+filename.replace("{xx}","").replace("{yy}","")
                                with open(os.path.join(subdir, 'TileConfiguration.registered.txt'),'r') as infile:
                                        with open(os.path.join(subdir, 'TileConfiguration.registered_copy.txt'),'w') as outfile:
                                                for line in infile:
                                                        line=line.replace(permprefix,thisprefix)
                                                        line=line.replace(permsuffix,thissuffix)
                                                        outfile.write(line)

                                IJ.run("Grid/Collection stitching", copy_grid_instructions)
                                im=IJ.getImage()
                                #Tighten the border
                                IJ.setThreshold(1,65535)
                                IJ.run("Create Selection")
                                IJ.run("Crop")
                                im0=IJ.getImage()
                                #chop off the bottom and right
                                #Change per quarter
                                IJ.makeRectangle(0,0,im0.width-pixels_to_crop,im0.height-pixels_to_crop)
                                im1=im0.crop()
                                width = str(int(round(im1.width*float(scalingstring))))
                                height = str(int(round(im1.height*float(scalingstring))))
                                print("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                time.sleep(15)
                                im2=IJ.getImage()
                                #Chnage per quarter
                                print("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Bottom-Right zero")
                                IJ.run("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Bottom-Right zero")
                                time.sleep(15)
                                im3=IJ.getImage()
                                savefile(im3,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                                im=IJ.getImage()
                                print("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.run("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.getImage()
                                savefile(im_10,os.path.join(downsample_subdir,fileoutname),plugin,compress=compress)
                                IJ.run("Close All")
                                im=IJ.open(os.path.join(out_subdir,fileoutname))
                                im = IJ.getImage()
                                tile_offset = upscaled_row_size - (tilesize * tiles_per_quarter)
                                for eachxtile in range(tiles_per_quarter):
                                        for eachytile in range(tiles_per_quarter):
                                                #Change per quarter
                                                each_tile_num = eachxtile*int(tileperside) + eachytile + 1
                                                #Change per quarter
                                                IJ.makeRectangle((eachxtile*tilesize)+tile_offset, (eachytile*tilesize)+tile_offset,tilesize,tilesize)
                                                im_tile=im.crop()
                                                savefile(im_tile,os.path.join(tile_subdir_persuf,thissuffixnicename+'_Site_'+str(each_tile_num)+'.tiff'),plugin,compress=compress)
                                IJ.run("Close All")

                        #top right quarter
                        print('Running top right')
                        #Change per quarter
                        standard_grid_instructions=["type=[Filename defined position] order=[Defined by filename         ] grid_size_x="+str(right_columns)+" grid_size_y="+top_rows+" tile_overlap="+overlap_pct+" first_file_index_x="+str(left_columns)+" first_file_index_y=0 directory="+subdir+" file_names=",
                        " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                        copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                        filename=permprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+permsuffix
                        #Change per quarter
                        fileoutname='StitchedTopRight'+filename.replace("{xx}","").replace("{yy}","")
                        IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                        im=IJ.getImage()
                        #We're going to overwrite this file later, but it gives us a chance for an early checkpoint
                        #This doesn't seem to play nicely with the compression option on, it doesn't get overwritten later and bad things happen
                        if compress.lower()!='true':
                                savefile(im,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                        IJ.run("Close All")
                        for eachpresuf in presuflist:
                                thisprefix, thissuffix=eachpresuf
                                thissuffixnicename = thissuffix.split('.')[0]
                                if thissuffixnicename[0]=='_':
                                        thissuffixnicename=thissuffixnicename[1:]
                                tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)
                                if not os.path.exists(tile_subdir_persuf):
                                        os.mkdir(tile_subdir_persuf)
                                filename=thisprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+thissuffix
                                #Change per quarter
                                fileoutname='StitchedTopRight'+filename.replace("{xx}","").replace("{yy}","")
                                with open(os.path.join(subdir, 'TileConfiguration.registered.txt'),'r') as infile:
                                        with open(os.path.join(subdir, 'TileConfiguration.registered_copy.txt'),'w') as outfile:
                                                for line in infile:
                                                        line=line.replace(permprefix,thisprefix)
                                                        line=line.replace(permsuffix,thissuffix)
                                                        outfile.write(line)

                                IJ.run("Grid/Collection stitching", copy_grid_instructions)
                                im=IJ.getImage()
                                #Tighten the border
                                IJ.setThreshold(1,65535)
                                IJ.run("Create Selection")
                                IJ.run("Crop")
                                im0=IJ.getImage()
                                #chop off the bottom and left
                                #Change per quarter
                                IJ.makeRectangle(pixels_to_crop,0,im0.width-pixels_to_crop,im0.height-pixels_to_crop)
                                im1=im0.crop()
                                width = str(int(round(im1.width*float(scalingstring))))
                                height = str(int(round(im1.height*float(scalingstring))))
                                print("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                time.sleep(15)
                                im2=IJ.getImage()
                                #Chnage per quarter
                                print("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Bottom-Left zero")
                                IJ.run("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Bottom-Left zero")
                                time.sleep(15)
                                im3=IJ.getImage()
                                savefile(im3,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                                im=IJ.getImage()
                                print("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.run("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.getImage()
                                savefile(im_10,os.path.join(downsample_subdir,fileoutname),plugin,compress=compress)
                                IJ.run("Close All")
                                im=IJ.open(os.path.join(out_subdir,fileoutname))
                                im = IJ.getImage()
                                tile_offset = upscaled_row_size - (tilesize * tiles_per_quarter)
                                for eachxtile in range(tiles_per_quarter):
                                        for eachytile in range(tiles_per_quarter):
                                                #Change per quarter
                                                each_tile_num = int(tiles_per_quarter)*int(tileperside)+ eachxtile*int(tileperside) + eachytile + 1
                                                #Change per quarter
                                                IJ.makeRectangle((eachxtile*tilesize), (eachytile*tilesize)+tile_offset,tilesize,tilesize)
                                                im_tile=im.crop()
                                                savefile(im_tile,os.path.join(tile_subdir_persuf,thissuffixnicename+'_Site_'+str(each_tile_num)+'.tiff'),plugin,compress=compress)
                                IJ.run("Close All")

                        #bottom left quarter
                        print('Running bottom left')
                        #Change per quarter
                        standard_grid_instructions=["type=[Filename defined position] order=[Defined by filename         ] grid_size_x="+str(left_columns)+" grid_size_y="+bot_rows+" tile_overlap="+overlap_pct+" first_file_index_x=0 first_file_index_y="+top_rows+" directory="+subdir+" file_names=",
                        " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                        copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                        filename=permprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+permsuffix
                        #Change per quarter
                        fileoutname='StitchedBottomLeft'+filename.replace("{xx}","").replace("{yy}","")
                        IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                        im=IJ.getImage()
                        #We're going to overwrite this file later, but it gives us a chance for an early checkpoint
                        #This doesn't seem to play nicely with the compression option on, it doesn't get overwritten later and bad things happen
                        if compress.lower()!='true':
                                savefile(im,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                        IJ.run("Close All")
                        for eachpresuf in presuflist:
                                thisprefix, thissuffix=eachpresuf
                                thissuffixnicename = thissuffix.split('.')[0]
                                if thissuffixnicename[0]=='_':
                                        thissuffixnicename=thissuffixnicename[1:]
                                tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)
                                if not os.path.exists(tile_subdir_persuf):
                                        os.mkdir(tile_subdir_persuf)
                                filename=thisprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+thissuffix
                                #Change per quarter
                                fileoutname='StitchedBottomLeft'+filename.replace("{xx}","").replace("{yy}","")
                                with open(os.path.join(subdir, 'TileConfiguration.registered.txt'),'r') as infile:
                                        with open(os.path.join(subdir, 'TileConfiguration.registered_copy.txt'),'w') as outfile:
                                                for line in infile:
                                                        line=line.replace(permprefix,thisprefix)
                                                        line=line.replace(permsuffix,thissuffix)
                                                        outfile.write(line)

                                IJ.run("Grid/Collection stitching", copy_grid_instructions)
                                im=IJ.getImage()
                                #Tighten the border
                                IJ.setThreshold(1,65535)
                                IJ.run("Create Selection")
                                IJ.run("Crop")
                                im0=IJ.getImage()
                                #chop off the top and right
                                #Change per quarter
                                IJ.makeRectangle(0,pixels_to_crop,im0.width-pixels_to_crop,im0.height-pixels_to_crop)
                                im1=im0.crop()
                                width = str(int(round(im1.width*float(scalingstring))))
                                height = str(int(round(im1.height*float(scalingstring))))
                                print("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                time.sleep(15)
                                im2=IJ.getImage()
                                #Chnage per quarter
                                print("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Top-Right zero")
                                IJ.run("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Top-Right zero")
                                time.sleep(15)
                                im3=IJ.getImage()
                                savefile(im3,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                                im=IJ.getImage()
                                print("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.run("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.getImage()
                                savefile(im_10,os.path.join(downsample_subdir,fileoutname),plugin,compress=compress)
                                IJ.run("Close All")
                                im=IJ.open(os.path.join(out_subdir,fileoutname))
                                im = IJ.getImage()
                                tile_offset = upscaled_row_size - (tilesize * tiles_per_quarter)
                                for eachxtile in range(tiles_per_quarter):
                                        for eachytile in range(tiles_per_quarter):
                                                #Change per quarter
                                                each_tile_num = eachxtile*int(tileperside) + int(tiles_per_quarter) + eachytile + 1
                                                #Change per quarter
                                                IJ.makeRectangle((eachxtile*tilesize)+tile_offset, (eachytile*tilesize),tilesize,tilesize)
                                                im_tile=im.crop()
                                                savefile(im_tile,os.path.join(tile_subdir_persuf,thissuffixnicename+'_Site_'+str(each_tile_num)+'.tiff'),plugin,compress=compress)
                                IJ.run("Close All")

                        #bottom right quarter
                        print('Running bottom right')
                        #Change per quarter
                        standard_grid_instructions=["type=[Filename defined position] order=[Defined by filename         ] grid_size_x="+str(right_columns)+" grid_size_y="+bot_rows+" tile_overlap="+overlap_pct+" first_file_index_x="+str(left_columns)+" first_file_index_y="+top_rows+" directory="+subdir+" file_names=",
                        " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                        copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                        filename=permprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+permsuffix
                        #Change per quarter
                        fileoutname='StitchedBottomRight'+filename.replace("{xx}","").replace("{yy}","")
                        IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                        im=IJ.getImage()
                        #We're going to overwrite this file later, but it gives us a chance for an early checkpoint
                        #This doesn't seem to play nicely with the compression option on, it doesn't get overwritten later and bad things happen
                        if compress.lower()!='true':
                                savefile(im,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                        IJ.run("Close All")
                        for eachpresuf in presuflist:
                                thisprefix, thissuffix=eachpresuf
                                thissuffixnicename = thissuffix.split('.')[0]
                                if thissuffixnicename[0]=='_':
                                        thissuffixnicename=thissuffixnicename[1:]
                                tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)
                                if not os.path.exists(tile_subdir_persuf):
                                        os.mkdir(tile_subdir_persuf)
                                filename=thisprefix+'_Well_'+eachwell+'_x_{xx}_y_{yy}_'+thissuffix
                                #Change per quarter
                                fileoutname='StitchedBottomRight'+filename.replace("{xx}","").replace("{yy}","")
                                with open(os.path.join(subdir, 'TileConfiguration.registered.txt'),'r') as infile:
                                        with open(os.path.join(subdir, 'TileConfiguration.registered_copy.txt'),'w') as outfile:
                                                for line in infile:
                                                        line=line.replace(permprefix,thisprefix)
                                                        line=line.replace(permsuffix,thissuffix)
                                                        outfile.write(line)

                                IJ.run("Grid/Collection stitching", copy_grid_instructions)
                                im=IJ.getImage()
                                #Tighten the border
                                IJ.setThreshold(1,65535)
                                IJ.run("Create Selection")
                                IJ.run("Crop")
                                im0=IJ.getImage()
                                #chop off the top and left
                                #Change per quarter
                                IJ.makeRectangle(pixels_to_crop,pixels_to_crop,im0.width-pixels_to_crop,im0.height-pixels_to_crop)
                                im1=im0.crop()
                                width = str(int(round(im1.width*float(scalingstring))))
                                height = str(int(round(im1.height*float(scalingstring))))
                                print("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+width+" height="+height+" interpolation=Bilinear average create")
                                time.sleep(15)
                                im2=IJ.getImage()
                                #Chnage per quarter
                                print("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Top-Left zero")
                                IJ.run("Canvas Size...", "width="+str(upscaled_col_size)+" height="+str(upscaled_row_size)+" position=Top-Left zero")
                                time.sleep(15)
                                im3=IJ.getImage()
                                savefile(im3,os.path.join(out_subdir,fileoutname),plugin,compress=compress)
                                im=IJ.getImage()
                                print("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.run("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                                im_10=IJ.getImage()
                                savefile(im_10,os.path.join(downsample_subdir,fileoutname),plugin,compress=compress)
                                IJ.run("Close All")
                                im=IJ.open(os.path.join(out_subdir,fileoutname))
                                im = IJ.getImage()
                                tile_offset = upscaled_row_size - (tilesize * tiles_per_quarter)
                                for eachxtile in range(tiles_per_quarter):
                                        for eachytile in range(tiles_per_quarter):
                                                #Change per quarter
                                                each_tile_num = int(tiles_per_quarter)*int(tileperside) +eachxtile*int(tileperside)+ int(tiles_per_quarter) + eachytile + 1
                                                #Change per quarter
                                                IJ.makeRectangle((eachxtile*tilesize), (eachytile*tilesize),tilesize,tilesize)
                                                im_tile=im.crop()
                                                savefile(im_tile,os.path.join(tile_subdir_persuf,thissuffixnicename+'_Site_'+str(each_tile_num)+'.tiff'),plugin,compress=compress)
                                IJ.run("Close All")

        else:
                print("Must identify well as round or square")
else:
        print("Could not find input directory ",subdir)
for eachlogfile in ['TileConfiguration.txt','TileConfiguration.registered.txt','TileConfiguration.registered_copy.txt']:
        os.rename(os.path.join(subdir,eachlogfile),os.path.join(out_subdir,eachlogfile))

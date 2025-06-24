#@String input_file_location
#@String step_to_stitch
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
#@String quarter_if_round
#@String final_tile_size
#@String xoffset_tiles
#@String yoffset_tiles
#@String compress

from ij import IJ, WindowManager
import os


row_widths = [5,7,7,7,7,7,5]
imagesize = 2960
tilesize = 1480*float(scalingstring) # barcoding acquisition size * scaling string

top_outfolder = 'output'
if not os.path.exists(top_outfolder):
        os.mkdir(top_outfolder)
# Define and create the parent folders where the images will be output
outfolder = os.path.join(top_outfolder,(step_to_stitch + '_stitched'))
tile_outdir = os.path.join(top_outfolder,(step_to_stitch + '_cropped'))
if not os.path.exists(outfolder):
        os.mkdir(outfolder)
if not os.path.exists(tile_outdir):
        os.mkdir(tile_outdir)
# Define and create the batch-specific subfolders where the images will be output
out_subdir=os.path.join(outfolder, out_subdir_tag)
tile_subdir=os.path.join(tile_outdir, out_subdir_tag)
if not os.path.exists(out_subdir):
        os.mkdir(out_subdir)
if not os.path.exists(tile_subdir):
        os.mkdir(tile_subdir)
		
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
        for presuf in presuflist:
                if channame in presuf[1]:
                        firstpresuf = presuf
        # make sure channame is processed first
        presuflist.remove(firstpresuf)
        presuflist.insert(0, firstpresuf)
        print (welllist, presuflist)

        for well in welllist:
                firstchan = True
                for eachpresuf in presuflist: # for each channel
                        thisprefix, thissuffix=eachpresuf
                        thissuffixnicename = thissuffix.split('.')[0]
                        if thissuffixnicename[0]=='_':
                                thissuffixnicename=thissuffixnicename[1:]
                        tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)

                        # INSTEAD OF RENUMBERING, PAD NARROW ROWS
                        # stitch images into rows
                        rownum = 1
                        startnum = 0
                        for rowlen in row_widths:
                                filename=thisprefix+'_Well_'+well+'_Site_{i}_'+thissuffix
                                fileoutname='Stitched'+filename.replace("Site_{i}","Row_"+str(rownum))
                                if firstchan:
                                        if rownum % 2 != 0: 
                                                order = "Left & Up"
                                        else:
                                                order = "Right & Up"
                                        standard_grid_instructions=["type=[Grid: snake by rows] order=["+order+"] grid_size_x="+str(rowlen)+" grid_size_y=1 tile_overlap="+str(overlap_pct)+" first_file_index_i="+str(startnum)+" directory="+out_subdir+" file_names=",
                                        " output_textfile_name=TileConfiguration_Row"+str(rownum)+".txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                                        IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                                        startnum += rowlen
                                else:
                                        # use the stitching from the first channel
                                        with open(os.path.join(out_subdir, "TileConfiguration_Row"+str(rownum)+".registered.txt"),'r') as infile:
                                                with open(os.path.join(out_subdir, "TileConfiguration_Row"+str(rownum)+".registered_copy.txt"),'w') as outfile:
                                                        for line in infile:
                                                                line=line.replace(firstpresuf,eachpresuf)
                                                                outfile.write(line)
                                        copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+out_subdir+" layout_file=TileConfiguration_Row"+str(rownum)+".registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                                        IJ.run("Grid/Collection stitching", copy_grid_instructions)
                                        # make width consistent post-stitching
                                        im=IJ.getImage()
                                        height = im.getHeight()
                                        width = imagesize*max(row_widths)
                                        IJ.run("Canvas Size...", "width="+str(width)+" height="+str(height)+" position=Center zero")
                                
                                # check that it didn't have gross error
                                height = im.getHeight()
                                if height > 1.1*imagesize:
                                        print("Gross failure stitching row "+str(rownum)+" of well "+well)
                                
                                IJ.saveAs(im, "tiff", os.path.join(out_subdir,fileoutname))
                                rownum += 1
                                IJ.run("Close All")

                        # now stitch the rows together
                        filename="Stitched"+thisprefix+"_Well_"+well+"_Row_{i}_"+thissuffix
                        fileoutname='WholeWell'+filename.replace("Row_{i}_","")
                        if firstchan:
                                standard_grid_instructions=["type=[Grid: snake by rows] order=[Left & Up] grid_size_x=1 grid_size_y=7 tile_overlap="+str(overlap_pct)+" first_file_index_i=1 directory="+out_subdir+" file_names=",
                                " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                                IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                        else:
                                with open(os.path.join(out_subdir, "TileConfiguration.registered.txt"),'r') as infile:
                                        with open(os.path.join(out_subdir, "TileConfiguration.registered_copy.txt"),'w') as outfile:
                                                for line in infile:
                                                        line=line.replace(firstpresuf,eachpresuf)
                                                        outfile.write(line)
                                copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+out_subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                                IJ.run("Grid/Collection stitching", copy_grid_instructions)
                        im=IJ.getImage()

                        # check that it didn't have gross error
                        height = im.getHeight()
                        width = im.getWidth()
                        if abs(height - width) > .2*imagesize*max(row_widths):
                                print("Gross failure stitching whole well "+well)

                        # make size consistent post-stitching
                        IJ.run("Canvas Size...", "width="+str(imagesize*max(row_widths))+" height="+str(imagesize*len(row_widths))+" position=Center zero")
                        IJ.saveAs(im, "tiff",os.path.join(out_subdir,fileoutname))

                        # crop to tiles that match barcoding image acquisition tiles (after they are scaled)
                        # hardcoded for 9 images per well, starting lower right, snake
                        # 0 counting to match non-stitch-crop barcoding
                        # IJ.makeRectangle starts at upper left
                        center = (imagesize*max(row_widths))/2
                        im=IJ.getImage()
                        # center (4)
                        IJ.makeRectangle(center-(tilesize/2), center-(tilesize/2),tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch4'+filename.replace("Row_{i}_","")))
                        # 3
                        IJ.makeRectangle(center-(tilesize/2)-imagesize*2, center-(tilesize/2),tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch3'+filename.replace("Row_{i}_","")))
                        # 5
                        IJ.makeRectangle(center+(tilesize/2), center-(tilesize/2),tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch5'+filename.replace("Row_{i}_","")))
                        # 0
                        IJ.makeRectangle(center+(tilesize/2), center+(tilesize/2),tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch0'+filename.replace("Row_{i}_","")))
                        # 1
                        IJ.makeRectangle(center-(tilesize/2), center+(tilesize/2),tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch1'+filename.replace("Row_{i}_","")))
                        # 2
                        IJ.makeRectangle(center-(tilesize/2)-imagesize*2, center+(tilesize/2),tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch2'+filename.replace("Row_{i}_","")))
                        # 6
                        IJ.makeRectangle(center+(tilesize/2), center-(tilesize/2)-imagesize*2,tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch6'+filename.replace("Row_{i}_","")))
                        # 7
                        IJ.makeRectangle(center-(tilesize/2), center-(tilesize/2)-imagesize*2,tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch7'+filename.replace("Row_{i}_","")))
                        # 8
                        IJ.makeRectangle(center-(tilesize/2)-imagesize*2, center-(tilesize/2)-imagesize*2,tilesize,tilesize)
                        im_tile=im.crop()
                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,'BCMatch8'+filename.replace("Row_{i}_","")))
                        
                        IJ.run("Close All")

                        # then crop each matched into 4 because the whole size is too large to run nicely in CellProfiler
                        for image in os.listdir(tile_subdir):
                                if 'BCMatch' in image:
                                        IJ.open(os.path.join(tile_subdir,image))
                                        im=IJ.getImage()

                                        # make crops, upper left, snake
                                        IJ.makeRectangle(0, 0,tilesize/2,tilesize/2)
                                        im_tile=im.crop()
                                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop0.tiff")))
                                        
                                        IJ.makeRectangle(tilesize/2, 0,tilesize/2,tilesize/2)
                                        im_tile=im.crop()
                                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop1.tiff")))
                                        
                                        IJ.makeRectangle(tilesize/2, tilesize/2,tilesize/2,tilesize/2)
                                        im_tile=im.crop()
                                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop2.tiff")))
                                        
                                        IJ.makeRectangle(0, tilesize/2,tilesize/2,tilesize/2)
                                        im_tile=im.crop()
                                        IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop3.tiff")))
                                        
                                        IJ.run("Close All")
                        firstchan = False
        print("done with well "+well)
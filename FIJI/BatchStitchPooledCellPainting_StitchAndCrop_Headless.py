#@String input_file_location
#@String subdir
#@String out_subdir_tag
#@String rows
#@String columns
#@String stitchorder
#@String scopename
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

from ij import IJ, WindowManager
import os
import string
import sys

top_outfolder = 'output'

if not os.path.exists(top_outfolder):
        os.mkdir(top_outfolder)

outfolder=os.path.join(top_outfolder,'images_corrected_stitched')
tile_outdir = os.path.join(top_outfolder,'images_corrected_cropped')
downsample_outdir = os.path.join(top_outfolder,'images_corrected_stitched_10X')
if not os.path.exists(outfolder):
        os.mkdir(outfolder)
if not os.path.exists(tile_outdir):
        os.mkdir(tile_outdir)
if not os.path.exists(downsample_outdir):
        os.mkdir(downsample_outdir)

stitchedsize=str(int(rows)*int(size))
if int(stitchedsize) > 46340:
        stitchedsize = '46340'
tileperside=int(tileperside)
upscaledsize=int(stitchedsize)*float(scalingstring)
if upscaledsize > 46340:
        upscaledsize = 46340
tilesize=int(int(upscaledsize)/tileperside)
tenxsize=str(int(upscaledsize/10))


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
        subdir = localtemp
        

if os.path.isdir(subdir):
        dirlist=os.listdir(subdir) 
        welllist=[]
        presuflist = []
        middledict = {}
        permprefix = None
        permsuffix = None
        if scopename=='TI-E':
                for eachfile in dirlist:
                        if '.tif' in eachfile:
                                if filterstring in eachfile:
                                        prefix1,suffix1=eachfile.split('MMStack_')
                                        prefix2,suffix2=suffix1.split('-')
                                        prefix3,suffix3=suffix2.split('ome')
                                        if prefix2 not in welllist:
                                                welllist.append(prefix2)
                                        if (prefix1,suffix3) not in presuflist:
                                                presuflist.append((prefix1,suffix3))
                                        if channame in eachfile:
                                                if permprefix == None:
                                                        permprefix = prefix1
                                                        permsuffix = suffix3
                presuflist.sort()
        else:
                for eachfile in dirlist:
                        if '.tif' in eachfile:
                                if filterstring in eachfile:
                                        prefixBeforeWell,suffixWithWell=eachfile.split('Well')
                                        Well,suffixAfterWell=suffixWithWell.split('_Channel')
                                        if Well not in welllist:
                                                welllist.append(Well)
                                        betweenWellAndSeries,suffixWithSeries=suffixAfterWell.split('Site_')
                                        Series,channelSuffix=suffixWithSeries.split('_')
                                        prefix1=prefixBeforeWell+'Well'+Well
                                        if (prefix1,channelSuffix) not in presuflist:
                                                presuflist.append((prefix1,channelSuffix))
                                                middledict[(prefix1,channelSuffix)]=betweenWellAndSeries
                                        if channame in channelSuffix:
                                                if permprefix == None:
                                                        permprefix=prefix1
                                                        permsuffix=channelSuffix
                presuflist.sort()	
        print welllist, presuflist

        for eachwell in welllist:
                in_subdir=subdir
                        
                standard_grid_instructions=["type=["+stitchorder+"] order=[Right & Down                ] grid_size_x="+rows+" grid_size_y="+columns+" tile_overlap="+overlap_pct+" first_file_index_i=0 directory="+in_subdir+" file_names=",
                " output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
                copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+in_subdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
                if scopename=='TI-E':
                        filename=permprefix+'MMStack_'+eachwell+"-Site_{i}.ome"+permsuffix
                else:
                        filename=permprefix +'_Channel'+ middledict[(permprefix,permsuffix)] + 'Site_{i}_' +permsuffix
                        
                fileoutname='Stitched'+filename.replace("{i}","")
                IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
                im=IJ.getImage()
                #We're going to overwrite this file later, but it gives is a chance for an early checkpoint
                IJ.saveAs(im,'tiff',os.path.join(out_subdir,fileoutname))
                IJ.run("Close All")
                for eachpresuf in presuflist:
                        thisprefix, thissuffix=eachpresuf
                        thissuffixnicename = thissuffix.split('.')[0]
                        if thissuffixnicename[0]=='_':
                                thissuffixnicename=thissuffixnicename[1:]
                        tile_subdir_persuf = os.path.join(tile_subdir,thissuffixnicename)
                        if not os.path.exists(tile_subdir_persuf):
                                os.mkdir(tile_subdir_persuf)
                        if scopename == 'TI-E':
                                filename=thisprefix+'MMStack_'+eachwell+"-Site_{i}.ome"+thissuffix
                        else:
                                filename = thisprefix + '_Channel' + middledict[eachpresuf] + 'Site_{i}_' + thissuffix
                        fileoutname='Stitched'+filename.replace("{i}","")
                        with open(os.path.join(in_subdir, 'TileConfiguration.registered.txt'),'r') as infile:
                                with open(os.path.join(in_subdir, 'TileConfiguration.registered_copy.txt'),'w') as outfile:
                                        for line in infile:
                                                line=line.replace(permprefix,thisprefix)
                                                line=line.replace(permsuffix,thissuffix)
                                                outfile.write(line)
                        
                        IJ.run("Grid/Collection stitching", copy_grid_instructions)
                        im=IJ.getImage()
                        IJ.run("Canvas Size...", "width="+stitchedsize+" height="+stitchedsize+" position=Top-Left zero")
                        im2=IJ.getImage()
                        IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+str(upscaledsize)+" height="+str(upscaledsize)+" interpolation=Bilinear average create")
                        im3=IJ.getImage()
                        IJ.saveAs(im3,'tiff',os.path.join(out_subdir,fileoutname))
                        im=IJ.getImage()
                        im_10=IJ.run("Scale...", "x=0.1 y=0.1 width="+str(im.width/10)+" height="+str(im.width/10)+" interpolation=Bilinear average create")
                        im_10=IJ.getImage()
                        IJ.saveAs(im_10,"Tiff",os.path.join(downsample_subdir,fileoutname))
                        IJ.run("Close All")
                        im=IJ.open(os.path.join(out_subdir,fileoutname))
                        im = IJ.getImage()
                        for eachxtile in range(tileperside):
                                for eachytile in range(tileperside):
                                        each_tile_num = eachxtile*tileperside + eachytile + 1
                                        IJ.makeRectangle(eachxtile*tilesize, eachytile*tilesize,tilesize,tilesize)
                                        im_tile=im.crop()
                                        IJ.saveAs(im_tile, "Tiff",os.path.join(tile_subdir_persuf,thissuffixnicename+'_Site_'+str(each_tile_num)+'.tiff'))
                        IJ.run("Close All")

else:
        print("Could not find input directory ",subdir)
for eachlogfile in ['TileConfiguration.txt','TileConfiguration.registered.txt','TileConfiguration.registered_copy.txt']:
        os.rename(os.path.join(subdir,eachlogfile),os.path.join(out_subdir,eachlogfile))

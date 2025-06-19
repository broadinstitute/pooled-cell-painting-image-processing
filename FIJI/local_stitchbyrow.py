from ij import IJ, WindowManager
import os

startchan = 'Mito'
chanlist = ['ER','Golgi','Mito','Phalloidin','DNA']
# single image with noise to pad rows to same length
padimage = "path/to/images_corrected/painting/padimage.tiff"
# location of the well folders of images to stitch
subdir = "path/to/images_corrected/painting/"
row_widths = [5,7,7,7,7,7,5]
overlap = 6
imagesize = 2960
welllist = ['B01','B02','B03','B04','B05','B06','B07']

tilesize = 1480*3.97 # barcoding acquisition size * scaling string

# make sure startchan is processed first
chanlist.remove(startchan)
chanlist.insert(0, startchan)

for well in welllist:
	wellsubdir = os.path.join(subdir,"Plate1-Well"+well)
	for chan in chanlist:
		# INSTEAD OF RENUMBERING, PAD NARROW ROWS
		# stitch images into rows
		rownum = 1
		startnum = 0
		for rowlen in row_widths:
			filename="Plate_Plate1_Well_"+well+"_Site_{i}_Corr"+chan+".tiff"
			fileoutname='Stitched'+filename.replace("Site_{i}","Row_"+str(rownum))
			if chan == startchan:
				if rownum % 2 != 0: 
					order = "Left & Up"
				else:
					order = "Right & Up"
				standard_grid_instructions=["type=[Grid: snake by rows] order=["+order+"] grid_size_x="+str(rowlen)+" grid_size_y=1 tile_overlap="+str(overlap)+" first_file_index_i="+str(startnum)+" directory="+wellsubdir+" file_names=",
				" output_textfile_name=TileConfiguration_Row"+str(rownum)+".txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
				IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
				startnum += rowlen
			else:
				# use the stitching from the first channel
				with open(os.path.join(wellsubdir, "TileConfiguration_Row"+str(rownum)+".registered.txt"),'r') as infile:
					with open(os.path.join(wellsubdir, "TileConfiguration_Row"+str(rownum)+".registered_copy.txt"),'w') as outfile:
						for line in infile:
							line=line.replace(startchan,chan)
							outfile.write(line)
				copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+wellsubdir+" layout_file=TileConfiguration_Row"+str(rownum)+".registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
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
			
			IJ.saveAs(im, "tiff", os.path.join(wellsubdir,fileoutname))
			rownum += 1
			IJ.run("Close All")

		# now stitch the rows together
		filename="StitchedPlate_Plate1_Well_"+well+"_Row_{i}_Corr"+chan+".tiff"
		fileoutname='WholeWell'+filename.replace("Row_{i}_","")
		if chan == startchan:
			standard_grid_instructions=["type=[Grid: snake by rows] order=[Left & Up] grid_size_x=1 grid_size_y=7 tile_overlap="+str(overlap)+" first_file_index_i=1 directory="+wellsubdir+" file_names=",
			" output_textfile_name=TileConfiguration.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 compute_overlap computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"]
			IJ.run("Grid/Collection stitching", standard_grid_instructions[0] + filename + standard_grid_instructions[1])
		else:
			with open(os.path.join(wellsubdir, "TileConfiguration.registered.txt"),'r') as infile:
				with open(os.path.join(wellsubdir, "TileConfiguration.registered_copy.txt"),'w') as outfile:
					for line in infile:
						line=line.replace(startchan,chan)
						outfile.write(line)
			copy_grid_instructions="type=[Positions from file] order=[Defined by TileConfiguration] directory="+wellsubdir+" layout_file=TileConfiguration.registered_copy.txt fusion_method=[Linear Blending] regression_threshold=0.30 max/avg_displacement_threshold=2.50 absolute_displacement_threshold=3.50 ignore_z_stage computation_parameters=[Save computation time (but use more RAM)] image_output=[Fuse and display]"
			IJ.run("Grid/Collection stitching", copy_grid_instructions)
		im=IJ.getImage()

		# check that it didn't have gross error
		height = im.getHeight()
		width = im.getWidth()
		if abs(height - width) > .2*imagesize*max(row_widths):
			print("Gross failure stitching whole well "+well)

		# make size consistent post-stitching
		IJ.run("Canvas Size...", "width="+str(imagesize*max(row_widths))+" height="+str(imagesize*len(row_widths))+" position=Center zero")
		IJ.saveAs(im, "tiff",os.path.join(wellsubdir,fileoutname))

		# crop to tiles that match barcoding image acquisition tiles (after they are scaled)
		# hardcoded for 9 images per well, starting lower right, snake
		# 0 counting to match non-stitch-crop barcoding
		# IJ.makeRectangle starts at upper left
		center = (imagesize*max(row_widths))/2
		im=IJ.getImage()
		# center (4)
		IJ.makeRectangle(center-(tilesize/2), center-(tilesize/2),tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch4'+filename.replace("Row_{i}_","")))
		# 3
		IJ.makeRectangle(center-(tilesize/2)-imagesize*2, center-(tilesize/2),tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch3'+filename.replace("Row_{i}_","")))
		# 5
		IJ.makeRectangle(center+(tilesize/2), center-(tilesize/2),tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch5'+filename.replace("Row_{i}_","")))
		# 0
		IJ.makeRectangle(center+(tilesize/2), center+(tilesize/2),tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch0'+filename.replace("Row_{i}_","")))
		# 1
		IJ.makeRectangle(center-(tilesize/2), center+(tilesize/2),tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch1'+filename.replace("Row_{i}_","")))
		# 2
		IJ.makeRectangle(center-(tilesize/2)-imagesize*2, center+(tilesize/2),tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch2'+filename.replace("Row_{i}_","")))
		# 6
		IJ.makeRectangle(center+(tilesize/2), center-(tilesize/2)-imagesize*2,tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch6'+filename.replace("Row_{i}_","")))
		# 7
		IJ.makeRectangle(center-(tilesize/2), center-(tilesize/2)-imagesize*2,tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch7'+filename.replace("Row_{i}_","")))
		# 8
		IJ.makeRectangle(center-(tilesize/2)-imagesize*2, center-(tilesize/2)-imagesize*2,tilesize,tilesize)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,'BCMatch8'+filename.replace("Row_{i}_","")))
		
		IJ.run("Close All")

		# then crop each matched into 4 because the whole size is too large to run nicely in CellProfiler
		for image in os.listdir(wellsubdir):
			if 'BCMatch' in image:
				IJ.open(os.path.join(wellsubdir,image))
				im=IJ.getImage()

				# make crops, upper left, snake
				IJ.makeRectangle(0, 0,tilesize/2,tilesize/2)
				im_tile=im.crop()
				IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,image.replace('.tiff',"Crop0.tiff")))
				
				IJ.makeRectangle(tilesize/2, 0,tilesize/2,tilesize/2)
				im_tile=im.crop()
				IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,image.replace('.tiff',"Crop1.tiff")))
				
				IJ.makeRectangle(tilesize/2, tilesize/2,tilesize/2,tilesize/2)
				im_tile=im.crop()
				IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,image.replace('.tiff',"Crop2.tiff")))
				
				IJ.makeRectangle(0, tilesize/2,tilesize/2,tilesize/2)
				im_tile=im.crop()
				IJ.saveAs(im_tile,"tiff", os.path.join(wellsubdir,image.replace('.tiff',"Crop3.tiff")))
				
				IJ.run("Close All")

print("done")
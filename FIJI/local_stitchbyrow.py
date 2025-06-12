from ij import IJ, WindowManager
import os

startchan = 'Mito'
chanlist = ['ER','Golgi','Mito','Phalloidin','DNA']
# single image with noise to pad rows to same length
padimage = "path/to/images_corrected/painting/padimage.tiff"
# location of the well folders of images to stitch
subdir = "path/to/images_corrected/painting/"
row_widths = [5,7,7,7,7,7,5]
welllist = ['A01','A02','A03','A04','A05','A06','A07','A08','A09','A10','A11','A12','B01','B02','B03','B04','B05','B06','B07','B08','B09','B10','B11','B12']

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
			print (chan, rowlen)
			if chan == startchan:
				print (startnum)
				if rownum % 2 != 0: 
					order = "Left & Up"
				else:
					order = "Right & Up"
				standard_grid_instructions=["type=[Grid: snake by rows] order=["+order+"] grid_size_x="+str(rowlen)+" grid_size_y=1 tile_overlap=7 first_file_index_i="+str(startnum)+" directory="+wellsubdir+" file_names=",
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
			im=IJ.getImage()
			if rowlen != max(row_widths):
				padnum = max(row_widths)-rowlen
				width = 2960*.94*max(row_widths)
				im=IJ.getImage()
				height = im.getHeight()
				IJ.run("Canvas Size...", "width="+str(width)+" height="+str(height)+" position=Center zero")
			
			IJ.saveAs(im, "tiff", os.path.join(wellsubdir,fileoutname))
			rownum += 1
			IJ.run("Close All")		

		# now stitch the rows together
		filename="StitchedPlate_Plate1_Well_"+well+"_Row_{i}_Corr"+chan+".tiff"
		fileoutname='WholeWell'+filename.replace("Row_{i}_","")
		if chan == startchan:
			standard_grid_instructions=["type=[Grid: snake by rows] order=[Left & Up] grid_size_x=1 grid_size_y=7 tile_overlap=7 first_file_index_i=1 directory="+wellsubdir+" file_names=",
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
		IJ.saveAs(im, "tiff",os.path.join(wellsubdir,fileoutname))
		IJ.run("Close All")
		
print("done")
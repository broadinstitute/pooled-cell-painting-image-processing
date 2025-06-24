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

from ij import IJ
import os

row_widths = [5,7,7,7,7,7,5]
fullsize = int(1480*float(scalingstring)) # barcoding acquisition size * scaling string

top_outfolder = 'output'
if not os.path.exists(top_outfolder):
	os.mkdir(top_outfolder)

# Define and create the parent folders where the images will be output
tile_outdir = os.path.join(top_outfolder,(step_to_stitch + '_cropped'))
if not os.path.exists(tile_outdir):
	os.mkdir(tile_outdir)
# Define and create the batch-specific subfolders where the images will be output
tile_subdir=os.path.join(tile_outdir, out_subdir_tag)
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

for image in os.listdir(subdir):
	if '.tiff' in image:
		IJ.open(os.path.join(subdir,image))
		IJ.run("Scale...", "x="+scalingstring+" y="+scalingstring+" width="+str(fullsize)+" height="+str(fullsize)+" interpolation=Bilinear average create")
		im = IJ.getImage()

		# make crops, upper left, snake
		IJ.makeRectangle(0, 0,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop0.tiff")))

		IJ.makeRectangle(fullsize/2, 0,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop1.tiff")))

		IJ.makeRectangle(fullsize/2, fullsize/2,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop2.tiff")))

		IJ.makeRectangle(0, fullsize/2,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(tile_subdir,image.replace('.tiff',"_Crop3.tiff")))
		
		IJ.run("Close All")
print("Done with scaling and cropping")
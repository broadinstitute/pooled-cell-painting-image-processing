from ij import IJ
import os

wellsubdir = '/Users/eweisbar/Desktop/test/'
filename = 'test.tiff'

row_widths = [5,7,7,7,7,7,5]
fullsize = int(1480*3.97) # barcoding acquisition size * scaling string
imagesize = 2960
center = (imagesize*max(row_widths))/2

folder = '/path/to/images_corrected/barcoding/Plate1-WellC01'
for image in os.listdir(folder):
	if '.tiff' in image:
		IJ.open(os.path.join(folder,image))
		IJ.run("Scale...", "x=3.97 y=3.97 width="+str(fullsize)+" height="+str(fullsize)+" interpolation=Bilinear average create")
		im = IJ.getImage()

		# make crops, upper left, snake
		IJ.makeRectangle(0, 0,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(folder,image.replace('.tiff',"Crop0.tiff")))

		IJ.makeRectangle(fullsize/2, 0,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(folder,image.replace('.tiff',"Crop1.tiff")))

		IJ.makeRectangle(fullsize/2, fullsize/2,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(folder,image.replace('.tiff',"Crop2.tiff")))

		IJ.makeRectangle(0, fullsize/2,fullsize/2,fullsize/2)
		im_tile=im.crop()
		IJ.saveAs(im_tile,"tiff", os.path.join(folder,image.replace('.tiff',"Crop3.tiff")))
		
		IJ.run("Close All")
print("Done with scaling and cropping")
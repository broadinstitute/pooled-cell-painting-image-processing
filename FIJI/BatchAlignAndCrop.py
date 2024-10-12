#@String input_file_location
#@String step_to_align
#@String subdir
#@String out_subdir_tag
#@String tileperside
#@String stitchmethod
#@String filterstring
#@String awsdownload
#@String bucketname
#@String localtemp
#@String downloadfilter

from ij import IJ, WindowManager
import os
import glob
import copy
import string
import sys
import time

top_outfolder = 'output'

if not os.path.exists(top_outfolder):
    os.mkdir(top_outfolder)

# Define and create the parent folders where the images will be output
outfolder = os.path.join(top_outfolder,(step_to_align + '_aligned'))
tile_outdir = os.path.join(top_outfolder,(step_to_align + '_aligned_cropped'))
if not os.path.exists(outfolder):
    os.mkdir(outfolder)
if not os.path.exists(tile_outdir):
    os.mkdir(tile_outdir)

# Define and create the batch-specific subfolders where the images will be output
out_subdir=os.path.join(outfolder, out_subdir_tag)
tile_subdir=os.path.join(tile_outdir, out_subdir_tag)
if not os.path.exists(tile_subdir):
    os.mkdir(tile_subdir)
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

rename_dict = {"CorrDNA.":"CorrDAPI.","Phalloidin.":"Phalloidin_A.","WGA.":"WGA_C.","ZEB1.":"ZEB1_G.","ZO1.":"ZO1_T."}
rename_dict_backwards = {v:k for k,v in rename_dict.items()}
rename_dict_backwards[".tiff.tif"]=".tiff"

quadrants =  ["BottomLeft", "BottomRight", "TopLeft","TopRight"]
target_channels = ["A", "C", "G", "T"]

quad_dict = {}
for quad in quadrants:
    quad_dict[quad]={"source":'(.*'+quad+'.*DAPI.*)','targets':[]}
    for target in target_channels:
        quad_dict[quad]['targets'].append('(.*'+quad+'.*_'+target+'\..*)')

def batch_fix_names(foldername,rename_dict):
    for i in glob.glob(foldername+"/*.ti*"):
        try:
            icopy = copy.deepcopy(i)
            for k in list(rename_dict.keys()):
                icopy = icopy.replace(k,rename_dict[k])
            os.rename(os.path.join(folder,i),os.path.join(folder,icopy))
        except:
            pass

def get_sizes(width,height,tiles_per_side):
    target_width = round(int(width)/(tiles_per_side))+1
    target_height = round(int(height)/(tiles_per_side))+1
    target_size = max(target_width,target_height)
    return target_size, target_size * tiles_per_side

def save_tiles(im,tiles_per_side,tilesize,filename_without_extension):
    im = IJ.getImage()
    for eachxtile in range(tiles_per_side):
        for eachytile in range(tiles_per_side):
            each_tile_num = eachxtile*tiles_per_side + eachytile + 1
            IJ.makeRectangle(eachxtile*tilesize, eachytile*tilesize,tilesize,tilesize)
            im_tile=im.crop()
            IJ.saveAs(im_tile,"Tiff",filename_without_extension+'_Site_'+str(each_tile_num)+'.tiff')
    IJ.run("Close All")


outdir = out_subdir
if not os.path.exists(outdir):
    os.makedirs(outdir)
outdir_cropped = tile_subdir
if not os.path.exists(outdir_cropped):
    os.makedirs(outdir_cropped)
matrix_file = os.path.join(subdir,"TransformationMatrices.txt")
batch_fix_names(subdir,rename_dict)
for quad in quadrants:
    im=IJ.run("Image Sequence...","open="+subdir+" virtual filter="+quad_dict[quad]["source"])
    im=IJ.getImage()
    tile_size, total_size = get_sizes(im.width,im.height,tileperside)
    window_name=os.path.split(os.path.normpath(subdir))[1]
    IJ.run(im,"MultiStackReg", "stack_1="+window_name+" action_1=Align file_1=["+matrix_file+"] stack_2=None action_2=Ignore file_2=[] transformation=["+stitchmethod+"] save")
    IJ.run("Canvas Size...", "width="+str(total_size)+" height="+str(total_size)+" position=Top-Left zero")
    time.sleep(15)
    im2=IJ.getImage()
    IJ.run("Image Sequence... ", "dir="+outdir+" format=TIFF use")
    batch_fix_names(outdir,rename_dict_backwards)
    IJ.run("Close All")
    for target in quad_dict[quad]["targets"]:
        print(target)
        im=IJ.run("Image Sequence...","open="+subdir+" virtual filter="+target)
        IJ.run(im,"MultiStackReg", "stack_1="+window_name+" action_1=[Load Transformation File] file_1=["+matrix_file+"] stack_2=None action_2=Ignore file_2=[] transformation=[Rigid Body]")
        IJ.run("Canvas Size...", "width="+str(total_size)+" height="+str(total_size)+" position=Top-Left zero")
        IJ.run("Image Sequence... ", "dir="+outdir+" format=TIFF use")
        batch_fix_names(outdir,rename_dict_backwards)
        IJ.run("Close All")
    to_tile = glob.glob(os.path.join(outdir,"*"+quad+"*"))
    for each_aligned in to_tile:
        outname = each_aligned.replace(out_subdir,tile_subdir).split('.')[0]
        im = IJ.open(each_aligned)
        save_tiles(im,tileperside,tile_size,outname)

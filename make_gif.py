from planet_common.raster import plimage
import numpy as np
from PIL import Image
import fnmatch
import os
import cv2



def open_file(file):
    img = plimage.load(filename=file)
    return img


def get_files(img_name, polygonize, aoi):
    files = []
    for f in os.listdir('.'):
        if polygonize < 2:
            if fnmatch.fnmatch(f, img_name+'*'+aoi+'.tif'):
                files.append(f)
        else:
            if fnmatch.fnmatch(f, img_name+'*.tif') and not fnmatch.fnmatch(f, img_name+'*'+aoi+'.tif'):
                files.append(f)
    return files


def make_jpg(day, file_name, outnum, type, date, aoi):
    date_str = date[4:6]+'/'+date[6:8]+'/'+date[0:4]
    file_col = '~/pl/planet_common/scripts/octave/'+type +"_color.txt"
    oufile_ndvi2 = "temp_color.tif"
    print(file_name+' on this day' +str(day))
    os.system('gdaldem color-relief  -b '+str(day)+' '+file_name+ ' '+file_col+' ' + oufile_ndvi2)

    if (day+outnum) < 10:
        oufile_pngt = '~/pl/planet_common/scripts/octave/'+aoi+'/jpegs/00'+str(day+outnum)+'.jpg'
    elif (day+outnum) < 100:
        oufile_pngt = '~/pl/planet_common/scripts/octave/'+aoi+'/jpegs/0'+str(day+outnum)+'.jpg'
    else:
        oufile_pngt = '~/pl/planet_common/scripts/octave/'+aoi+'/jpegs/'+str(day+outnum)+'.jpg'

    os.system('gdal_translate -q -of JPEG -b 1 -b 2 -b 3 '+oufile_ndvi2+' '+oufile_pngt)

    if (day+outnum) < 10:
        oufile_png = '~/pl/planet_common/scripts/octave/'+aoi+'/jpegs/00'+str(day+outnum)+'t.jpg'
    elif (day+outnum) < 100:
        oufile_png = '~/pl/planet_common/scripts/octave/'+aoi+'/jpegs/0'+str(day+outnum)+'t.jpg'
    else:
        oufile_png = '~/pl/planet_common/scripts/octave/'+aoi+'/jpegs/'+str(day+outnum)+'t.jpg'

    os.system('convert '+oufile_pngt+' -fill white -undercolor "#00000080" -gravity NorthEast \
              -pointsize 20 -annotate +50+50 '+date_str+' '+oufile_png)

    os.system('rm temp_color.tif')

    print(oufile_png)


def make_gif(gif_name,aoi):

    os.chdir('jpegs')
    delay = '20'
    name_gif = gif_name+'.gif'

    print('making gif')

    os.system('convert -limit memory 2MB -delay '+delay+' -loop 0 -resize 500x500 \
              -shave 5x5 *t.jpg '+"~/pl/planet_common/scripts/octave/"+aoi+"/"+name_gif)

    os.chdir('..')


def main(img_name, type, dates, aoi, polygonize):
    os.system("rm -R jpegs")
    os.system("mkdir jpegs")

    files = get_files(img_name, polygonize, aoi)
    files.sort()
    print("making gif with " +str(files))
    outnum = 0
    for file_name in files:
        file = open_file(file_name).bands
        for day in range(1,len(file)+1):
            if len(dates) > day+outnum-1:
                make_jpg(day, file_name, outnum, type, dates[day+outnum-1],aoi)
            else:
                print("extra scenes")

        outnum = outnum+len(file)

    make_gif(img_name, aoi)



# name_gif = outdir+str(args.aoi_id[0])+'_'+local_dir+'_rgb.gif'
# os.system('convert -limit memory 2MB -delay '+delay+' -loop 0 -resize 500x500 \
#           -shave 5x5 *rgb.jpg '+name_gif)



    # qgis_file.bands = [file[day]]
    # temp = str(file_name[:-4]+'_'+str(day)+'.tif')
    # qgis_file.save(temp)
    #
    # print(temp)

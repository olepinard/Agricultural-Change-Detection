import os
import fnmatch
import numpy as np
from argparse import ArgumentDefaultsHelpFormatter
from planet_common.raster import plimage
from sklearn.cluster import KMeans
from planet_common.client import storage
import ancillary_vm as ask
import math
import time
import gdal
import psutil
import make_gif as gif

gdal.UseExceptions()


'''
This function gets called in order to download the required files in order to
edit them in the functions below. When there is a group and the need to polygonize
the functions brings in two and merges them to have seemless transitions.
'''
def get_files(group, extra,type):
    if polygonize < 2:
        qgis_file = ask.open_file(type+"_"+img_type+"_"+aoi+".tif")
        return qgis_file
    else:
        if group >= 10:
            group0 = str(group)
            group1 = str(group+1)
        else:
            group0 = "0"+str(group)
            if (group+1) >= 10:
                group1 = str(group+1)
            else:
                group1 = "0"+str(group+1)

    if group == polygonize-1:
        qgis_file = ask.open_file(type+"_"+img_type+"_"+aoi+group0+".tif")
        return qgis_file
    else:
        qgis_file = ask.open_file(type+"_"+img_type+"_"+aoi+group0+".tif")
        length = len(qgis_file)
        qgis_file2 = ask.open_file(type+"_"+img_type+"_"+aoi+group1+".tif")
        for i in range(len(qgis_file2)):
            qgis_file.append(qgis_file2[i])

        if type == "ndvi" or type == "ndvi_full":
            if extra == 0:
                return qgis_file[:(length+noise_days)]
            if extra == 2:
                return qgis_file[:(length)]
            else:
                return qgis_file[:(length+change_days)]
        if type == "change":
            return qgis_file[:(length+change_days)]
        if type == "classify":
            return qgis_file[:(length+1)]


def get_file_size(group):
    if polygonize < 2:
        qgis_file = ask.open_file("ndvi_"+img_type+"_"+aoi+".tif")
        return len(qgis_file)
    else:
        if group >= 10:
            group0 = str(group)
        else:
            group0 = "0"+str(group)
        qgis_file = ask.open_file("ndvi_CESTEM_"+aoi+group0+".tif")
        return len(qgis_file)


def gif_maker(match,type):
    if match != 'ndvi_full':
        dates = ask.get_dates(bucket, date, "_cestem_sr_gapfree3_imperial.tif", vm)
    else:
        dates = ask.get_dates(bucket, date, match, vm)
    dates.sort()
    img_name = type+'_'+img_type+'_'+aoi
    gif.main(img_name, type, dates, aoi, polygonize)

    return "the "+type+" gif has been made!"




'''
This is called when the previous itterations of dates or classification is needed in
order to continue
'''
def get_old(group, file_type):
    if group >= 10:
        group = str(group)
    else:
        group = "0"+str(group)

    if polygonize < 2:
        file = file_type+"_"+img_type+"_"+aoi+".tif"
    else:
        file = file_type+"_"+img_type+"_"+aoi+group+".tif"
    img = gdal.Open(file).ReadAsArray()
    return img[-1]


'''
This will take the group and the file that needs to be saved and it creates the
names and saves the file properly
'''
def save(array, qgis_file, group, file_type):
    old_ref = gdal.Open(qgis_file, gdal.GA_ReadOnly)

    if polygonize < 2:
        filename = file_type+"_"+img_type+"_"+aoi+".tif"

    else:
        if group >= 10:
            group = str(group)
        else:
            group = "0"+str(group)
        filename = file_type+"_"+img_type+"_"+aoi+group+".tif"

    x_pixels = len(array[0][0])  # number of pixels in x
    y_pixels = len(array[0])  # number of pixels in y

    driver = gdal.GetDriverByName('GTiff')
    dataset = driver.Create(
        filename,
        x_pixels,
        y_pixels,
        len(array),
        gdal.GDT_UInt16)

    dataset.SetGeoTransform(old_ref.GetGeoTransform())
    dataset.SetProjection(old_ref.GetProjection())


'''
This is the function that actually calls all of the classifying functions Given
all of the right arrays
'''
def classed(change_stack, ndvi, file_num, old_class):
    track_day_change = []
    for i in range(change_days):
        track_day_change.append(ask.day_classify(change_stack[file_num-i], classify_threshold))
    new_class = ask.classify(track_day_change,time_change)
    return ask.classify_type(new_class, ndvi, old_class)

'''
This is the function that takes in the arrays and calculates the change between
them on a five day time scale
'''
def change(noise_days,img_stack, file_num):
    change = []
    for i in range(1,noise_days):
        change.append(img_stack[file_num-i] - img_stack[file_num-(i+1)])
    change = ((sum(change)/len(change))*1000).astype('int16')
    return change

'''
This takes in an individual file name and outputs an calculated ndvi array to
then be added and saved

'''
def ndviing(files, file_num, old_ndvi, cestem_files):
    bands = ask.open_ndvi(start_y,start_x,y_off,x_off, files[file_num], sub_img)
    ndvi_layer = ask.ndvi(bands)
    if img_type in ["TOAR","SR","HLS"]:
        no_nan = np.nan_to_num(ndvi_layer)
        if file_num > 0:
            if  img_type == "HLS":
                ndvi_nocloud = ask.cloud_to_zero(ndvi_layer, old_ndvi, bands[4], 1)
            else:
                #if this is erroring check the output of get_ndvi_files
                #this assumes the output is a array of strings looking like this:
                # cestem_data_packet.20180420_cestem_sr_gapfree2_arable_ne_aoi2.tif
                for cestem in cestem_files:
                    date_cestem = cestem.split('.')[1][:8]
                    date_sr = files[file_num].split('.')[1][:8]
                    if date_cestem == date_sr:
                        cestem_array = gdal.Open(cestem)
                        if sub_img:
                            cestem_array.subwindow(start_y,start_x,y_off,x_off)

                ndvi_nocloud = ask.cloud_to_zero(ndvi_layer, old_ndvi, cestem_array.ReadAsArray()[4], 0)

            return ndvi_nocloud
        else:
            return no_nan
    else:
        return ndvi_layer



'''
Given the classified image stack it calculates the most recent green up for every
pixel on any given day. It also keeps track of the number of greenups for every
pixel over the entire time period studied
'''
def green_up_dates(product_file,group, match, green_up_num, day):

    if sub_img:
        shape = np.zeros([x_off-start_x,y_off-start_y])
    else:
        shape = np.zeros(ask.get_shape(product_file))

    classify_stack = get_files(group, 0, 'classify')
    print('classified '+str(group)+' file has been brought in')
    print(str(len(classify_stack))+" files to ID green up")
    for file_num in range(1, len(classify_stack)):
        if file_num == 1 and group == 0:
            old_dates = shape
        elif file_num != 1:
            old_dates = classify_stack[file_num-2]
        else:
            old_dates = get_old(group-1, change_name)
        green_up_num =  ask.greened_num(classify_stack[file_num], classify_stack[file_num-1], green_up_num)

        classify_stack[file_num-1] = ask.greened(classify_stack[file_num],classify_stack[file_num-1], old_dates, day,change_index)

        process = psutil.Process(os.getpid())
        if process.memory_percent() > 65:
            print("near memory limit: "+ str(process.memory_percent()))
        day = day + 1



    save(classify_stack[:-1], product_file, group, change_name)
    if group == polygonize-1 or polygonize < 2:

        save([green_up_num], product_file, 0, change_name+"_num")
    return [day, green_up_num]


'''
This function utilizes the change function in order to classify where change
has occured. By observing multi-day change it is able to classify parts of the
image which are subject to change. The output is a stack of each day with three
classes, 0 equals to areas that have undergone no change, the -1 are areas where
vegetation levels have decrased and the 1 means that vegetation levels have
increased.
'''
def change_classifying(product_file,group):

    if sub_img:
        shape = np.zeros([x_off-start_x,y_off-start_y])
    else:
        shape = np.zeros(ask.get_shape(product_file))

    change_stack = get_files(group, 0, 'change')
    ndvi_stack = get_files(group, 1, 'ndvi_full')
    print('change '+str(group)+' file has been brought in')
    print(str(len(change_stack))+" files to calculate change")

    for file_num in range(change_days-1, len(change_stack)):
        if file_num == (change_days-1) and group == 0:
            old_class = shape
        elif file_num != (change_days-1):
            old_class = change_stack[file_num-change_days]
        else:
            old_class = get_old(group-1, "classify")
        print(file_num-(change_days-1))
        change_stack[file_num-(change_days-1)] = classed(change_stack, ndvi_stack[(file_num-(change_days-1))+noise_days], file_num, old_class)

        process = psutil.Process(os.getpid())
        if process.memory_percent() > 65:
            print("near memory limit: "+ str(process.memory_percent()))


    save(change_stack[:-change_days], product_file, group, "classify")



def ndvi_gapfill(cestem_dates, hls_dates, product_file, group, old_gapfill):
    # qgis_file = gdal.Open(product_file)
    # if sub_img:
    #     qgis_file.subwindow(start_y,start_x,y_off,x_off)

    hls_stack = get_files(group, 2, 'ndvi')
    cestem_num = get_file_size(group)
    print('hls file '+str(group)+' has been brought in')

    full_stack = []
    for file_num in range(1+group*len(hls_stack),group*len(hls_stack)+len(hls_stack)):
        gap = 0
        missing_days = 0

        print('hls_len'+str(len(hls_dates)))
        print('cestem_len'+str(len(cestem_dates)))
        print(cestem_dates[file_num-1+gap])
        while hls_dates[file_num-1] != cestem_dates[file_num-1+gap]:
            gap = gap+1
        print('hls_current_date'+str(hls_dates[file_num-1]))
        print('gap:'+str(gap))
        print('hls_next_date'+str(hls_dates[file_num]))
        if hls_dates[file_num] == hls_dates[file_num-1]:
            print("dual dates")
        else:
            while hls_dates[file_num] != cestem_dates[file_num+gap+missing_days]:
                print(cestem_dates[file_num+gap+missing_days])
                missing_days = missing_days+1

            missing = ask.linear_interpilation(missing_days+1, file_num-group*len(hls_stack), hls_stack)
            for arr in missing:
                full_stack.append(arr)

    full_stack.append(hls_stack[-1])
    save(full_stack, product_file, group, "ndvi_full")

'''
This function calculates the change between images and then averages it over
an N day period. Then saves a cumulitive stack of all the change rasters for
whatever directory specified. This can also be done as a comparison of CESTEM
versus TOAR or simply the directory entered. For TOAR the could mask of CESTEM
is used to mask out the clouds in order to lower noise. The change being
observed is in the ndvi calculation
'''
def change_stacking(product_file,group):

    # qgis_file = gdal.Open(product_file)
    # # if sub_img:
    # #     qgis_file.subwindow(start_y,start_x,y_off,x_off)
    #


    img_stack = get_files(group, 0, 'ndvi_full')
    print('ndvi file '+str(group)+' has been brought in')
    print(len(img_stack))
    for file_num in range(noise_days, len(img_stack)):
        img_stack[file_num-noise_days] = ask.gaussian_blur(change(noise_days,img_stack, file_num))

        process = psutil.Process(os.getpid())
        if process.memory_percent() > 65:
            print("near memory limit: "+ str(process.memory_percent()))


    save(img_stack[:-noise_days], product_file, group, "change")


'''
This function will take all of the images from the directory that you give it
and compute the ndvi for each image and then create a final stack with the ndvi
value of each image. Thus allowing to opservation of the plant health over time
once graphed. Two options are available, you can pick the directory to pick the
images from, and if you have a TOAR and CESTEM directory you can create a cestem
stack on only the days where a TOAR image was captured.
'''
def ndvi_stacking(files,group, old_ndvi, cestem_files):
    # qgis_file = gdal.Open(files[0])
    # if sub_img:
    #     qgis_file.subwindow(start_y,start_x,y_off,x_off)


    if polygonize < 2:
        stack = []
        for file_num in range(len(files)):
            print(files[file_num])
            if file_num > 0:
                old_ndvi = stack[-1]
            stack.append(ndviing(files, file_num, old_ndvi, cestem_files))
            process = psutil.Process(os.getpid())
            if process.memory_percent() > 65:
                print("near memory limit: "+ str(process.memory_percent()))


        save(stack, file[0], group, "ndvi")

    else:
        stack = []
        sec = int(len(files)/polygonize)
        print("section group:"+str(sec*(group+1)))
        for file_num in range(sec*group,sec*(group+1)):
            print(files[file_num] +" "+ str(file_num) +" "+ str(file_num-sec*group))
            if file_num > sec*group:
                old_ndvi = stack[file_num-(1+sec*group)]

            stack.append(ndviing(files, file_num, old_ndvi, cestem_files))
            process = psutil.Process(os.getpid())
            if process.memory_percent() > 65:
                print("near memory limit: "+ str(process.memory_percent()))

        save(stack, file[0],group,"ndvi")

    return old_ndvi

'''
This function takes in all of the files from a particular bucket and creates a
list of them. It only returns the files that fall within the perameters interested
in.
'''
def get_ndvi_files(match):
    if match == "30_%_imperial_1.tif":
        file_names = []
        file_names1 = ask.get_list(bucket, date, "%_L"+match, vm)
        file_names2 = ask.get_list(bucket, date, "%_S"+match, vm)
        file_names2.sort()
        file_names1.sort()
        for file in file_names2:
            file_names1.append(file)
        for num in range(1,len(file_names1)):
            if file_names1[num][13:21] != file_names1[num-1][13:21]:
                file_names.append(file_names1[num])

    else:
        file_names = ask.get_list(bucket, date, match, vm)


    print("aquiring " + str(len(file_names)) + " files")
    files = []

    for file in file_names:
        if os.path.isfile("/tmp/pl_storage_cache/"+bucket+"."+file):
            print(file +" is already downloaded")
            files.append("/tmp/pl_storage_cache/"+bucket+"."+file)
        else:
            print("aquiring: " +file)
            product_file=storage.get_scene_file(None,bucket,file,null_if_missing=False,refresh_time=600)
            files.append(product_file)
    return files


'''
This is the master funciton that is called and then delagates based on the
inputs. It also adjust to being in the right directory and gets the correct
list of files.
'''
def read_and_save(match):
    os.system("mkdir "+aoi)
    os.chdir(aoi)
    start_time = time.time()

    if ndvi_stack == True:
        if img_type == "CESTEM":
            files = get_ndvi_files(match)
            files.sort()
            cestem_files = files
        else:
            files = get_ndvi_files(match)
            files.sort()
            cestem_files = get_ndvi_files(CESTEM_match)
            cestem_files.sort()

        qgis_file = ask.get_file_meta(product_file)
        if sub_img:
            shape = np.zeros([x_off-start_x,y_off-start_y])
        else:
            shape = np.zeros(ask.get_shape(product_file))

        old_ndvi = shape




        if polygonize < 2:
            group = 0
            print("ndvi for one file")
            old_ndvi = ndvi_stacking(files,group, old_ndvi, cestem_files)

        else:
            for group in range(polygonize):
                print("ndvi group: "+str(group))
                old_ndvi = ndvi_stacking(files,group, old_ndvi, cestem_files)

        if make_gif == True:
            print(gif_maker(match,'ndvi'))

    if match == "30_%_imperial_1.tif":
        file_names = ask.get_list(bucket, date, "%_L"+match, vm)
    else:
        file_names = ask.get_list(bucket, date, match, vm)

    #hardcoded as we cant access buckets
    product_file =  "ndvi_CESTEM_imperial_large00.tif"


    if gapfill == True:
        hls_dates = ask.get_dates(bucket, date, match, vm)
        cestem_dates = ask.get_dates(bucket, date, CESTEM_match, vm)
        hls_dates.sort()
        cestem_dates.sort()
        old_gapfill = np.zeros(ask.get_shape(product_file))
        if polygonize < 2:
            group = 0
            print("gapfilling for one file")
            old_gapfill = ndvi_gapfill(cestem_dates, hls_dates, product_file, group, old_gapfill)

        else:
            for group in range(polygonize):
                print("gapfilling group: "+str(group))
                old_gapfill = ndvi_gapfill(cestem_dates, hls_dates, product_file, group, old_gapfill)

        if make_gif == True:
            print(gif_maker(match,'ndvi_full'))

    #Create a max ndvi function

    if change_stack == True:
        if polygonize < 2:
            group = 0
            print("change detection on one file")
            change_stacking(product_file,group)

        else:
            for group in range(polygonize):
                print("change detection group: "+str(group))
                change_stacking(product_file,group)
    if make_gif == True:
        print(gif_maker(match,'change'))

    if classified_stack == True:
        if polygonize < 2:
            group = 0
            print("classifying one file")
            change_classifying(product_file,group)

        else:
            for group in range(polygonize):
                print("classifying group: "+str(group))
                change_classifying(product_file,group)
    if make_gif == True:
        print(gif_maker(match,'classify'))

    if green_up == True:
        if sub_img:
            green_up_num = np.zeros([x_off-start_x,y_off-start_y])
        else:
            green_up_num = np.zeros(ask.get_shape(product_file))
        day = 0
        if polygonize < 2:
            group = 0
            print("calculating green up dates for one file")
            merge = green_up_dates(product_file,group, match,green_up_num, day)
            day = merge[0]
            green_up_num  = merge[1]

        else:
            for group in range(polygonize):
                print("calculating green up dates for group: "+str(group))
                merge = green_up_dates(product_file,group, match,green_up_num, day)
                day = merge[0]
                green_up_num = merge[1]
    if make_gif == True:
        print(gif_maker(match,'green_up'))

    print('------ The process took '+ str(((time.time() - start_time)/60))+' minutes ------' )









date = '2018%%'
TOAR_match = '_3B_AnalyticMS_TOAR_imperial.tif'
SR_match = '_3B_AnalyticMS_SR_imperial.tif'
HLS_match = '30_%_imperial_1.tif'
CESTEM_match = '_cestem_sr_gapfree3_imperial.tif'
bucket = 'octave_study'
img_type = "SR"
list_dump = "scene_list.txt"
aoi = "imperial_large"
ndvi_stack = True
gapfill =True
change_stack = True
classified_stack = True
green_up = True
change_name = "green_up"  #green up = 1/harvest = 2
change_index = 1
make_gif = True
vm = True
sub_img = False
start_y = 0
y_off = 1000
start_x = 0
x_off = 1000
classify_threshold = 20     #ndvi threshold for classification
time_change = 3             #number of day with change in a direction
polygonize = 30             #how many files to split into
noise_days = 5              #average the change to loose noise
change_days = 7             #time window being considered for classification

read_and_save(SR_match)





'''
date = '2018%%'
TOAR_match = '_3B_AnalyticMS_TOAR_imperial.tif'
SR_match = '_3B_AnalyticMS_SR_imperial.tif'
CESTEM_match = '_cestem_sr_gapfree2_imperial.tif'
bucket = 'cestem_farming'
img_type = "CESTEM"
list_dump = "scene_list.txt"
aoi = "year_large_farming"
ndvi_stack = False
change_stack = True
classified_stack = True
green_up = True
change_name = "green_up"  #green up = 1/harvest = 2
change_index = 1
make_gif = True
vm = True
sub_img = False
start_y = 1400
y_off = 1000
start_x = 900
x_off = 1000
classify_threshold = 20
polygonize = 20
noise_days = 4
change_days = 3





date = '2018%%'
TOAR_match = '_3B_AnalyticMS_TOAR_imperial.tif'
SR_match = '_3B_AnalyticMS_SR_imperial.tif'
CESTEM_match = '_cestem_sr_gapfree2_arable_ne_aoi2.tif'
bucket = 'cestem_data_packet'
img_type = "CESTEM"
list_dump = "scene_list.txt"
aoi = "nebraska"
ndvi_stack = False
change_stack = False
classified_stack = False
green_up = True
change_name = "green_up"  #green up = 1/harvest = 2
change_index = 1
make_gif = True
vm = True
sub_img = False
start_y = 0
y_off = 1361
start_x = 0
x_off = 1011
classify_threshold = 10
time_change = 5
polygonize = 5
noise_days = 5
change_days = 10
'''

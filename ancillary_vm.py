import os
import fnmatch
import numpy as np
from sklearn.cluster import KMeans
import math
import time
import gdal
import make_gif as gif
import cv2

gdal.UseExceptions()

def day_classify(x,num):
    if x >= num :
        return 1
    if x <= -num:
        return -1
    else:
        return 0
day_classify = np.vectorize(day_classify, otypes=[np.int16])

def classify(days,time_change):
    change_classed = day_classify(sum(days),time_change)
    return change_classed

def classify_type(new_class, ndvi, old_class):
    if old_class == 0:
        if new_class == 1:
            return 1
        if new_class == -1:
            return 2
        if new_class == 0 and ndvi > .5:
            return 3
        else:
            return 5
    else:
        if new_class == 1:
            return 1
        # if new_class == -1 and old_class in [1,2,3]:
        #     return 2
        if new_class == -1:
            return 2
        if new_class == 0 and ndvi >= .3 and old_class in [1,3] :
            return 3
        if new_class == 0 and old_class in [2,4] :
            return 4
        if new_class == 0 and old_class in [5,6]:
            return 5
        else:
            return 6
classify_type = np.vectorize(classify_type, otypes=[np.int16])

# def zero_to_num(no_nan, past):
#     return past if no_nan == 0 else no_nan
# zero_to_num = np.vectorize(zero_to_num)


def cloud_to_zero(ndvi_layer, old_ndvi, band, num):
    return ndvi_layer if band == num and ndvi_layer != 0 else old_ndvi
cloud_to_zero = np.vectorize(cloud_to_zero)



def greened_num(current, old, past):
    if past == 0:
        if current == 1:
            return 1
        else:
            return 0
    else:
        if current == 1 and old != 1:
            return past+1
        else:
            return past
greened_num = np.vectorize(greened_num, otypes=[np.int16])

def greened(current, old, old_date, date, num):
    if old_date == 0:
        if current == num:
            return date
        else:
            return 0
    else:
        if current == num and old != num:
            return date
        else:
            return old_date
greened = np.vectorize(greened, otypes=[np.int16])


def open_file(file):
    img = gdal.Open(file).ReadAsArray()
    return img

def get_shape(file):
        img = gdal.Open(file).ReadAsArray()
        return img[0].shape


def get_file_meta(file):
    img = gdal.Open(file)
    return img.GetMetadata()

def get_dates(bucket, date, match, vm):
    dates = []
    if match == "30_%_imperial_1.tif":
        file_names = get_list(bucket, date, "%_L"+match, vm)
        file_names2 = get_list(bucket, date, "%_S"+match, vm)
        file_names2.sort()
        file_names.sort()
        for file in file_names2:
            file_names.append(file)
        for num in range(1,len(file_names)):
            if file_names[num][13:21] != file_names[num-1][13:21]:
                dates.append(file_names[num][13:21])

    else:
        file_names = get_list(bucket, date, match, vm)
        for file in file_names:
            dates.append(file[:8])
    return dates

def linear_interpilation(missing_days, file_num, hls_stack):
    missing_stack = []
    hls_first = hls_stack[file_num-1]
    hls_second = hls_stack[file_num]
    missing_stack.append(hls_first)
    for i in range(1,missing_days):
        missing_stack.append((hls_second-hls_first)/(missing_days)*i+hls_first)


    return missing_stack





'''
for sub sampeling, although this has not been figured out
'''
def open_ndvi(start_width,start_length,end_width,end_length, file, sub_img):
    img = gdal.Open(file)
    if sub_img:
        img.subwindow(start_width,start_length,end_width,end_length)
    return img.ReadAsArray()






def gaussian_blur(file):
    blurred = cv2.GaussianBlur(file, (21,21),0)
    return blurred


'''
This function takes in a four band numpy array and returns a single ndvi array
'''
def ndvi(img):
    index = []
    red = np.array(img[2], dtype=np.float)
    NIR = np.array(img[3], dtype=np.float)
    index = (NIR - red)/(NIR + red)
    return index

def get_list(bucket, date, match, vm):
    os.system('rm scene_list.txt')

    if vm:
        os.system('~/pl/planet_common/scripts/pls.py -c pl list '+bucket+' --name-like '+date+match+' >> '+'scene_list.txt')
    else:
        os.system('/vagrant/scripts/pls.py -c pl list '+bucket+' --name-like '+date+match+' >> '+'scene_list.txt')

    scenes = []
    with open('scene_list.txt') as f:
        for line in f:
            scenes.append(line.strip())
    return scenes


'''
Finish this total ndvi thing
'''
def total_ndvi(ndvi_max, file_name):
    file = open_file(file_name)
    for img in file:
        ndvi_max = max_ndvi(ndvi_max,img)
    return ndvi_max

def max_ndvi(ndvi_max,img):
    if img > ndvi_max:
        return img
    else:
        return ndvi_max




def download(scenes, bucket):
    os.chdir("/vagrant/scripts/octave_img/flooding/CESTEM")
    for i in range(len(scenes)):
        os.system('/vagrant/scripts/pls.py -c pl download '+ bucket + " " + scenes[i])

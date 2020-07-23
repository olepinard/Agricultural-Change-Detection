# Agricultural Change Detection

## Image Processing
>Given a folder filled with daily satelite imagery of an AOI the change_vm.py script will calculate the NDVI for all images and create a new image where each band 
>is a different date. This code can work for as large of a dataset as available and can subdivide the tasks in order to not overload the computers RAM.
>In order to sudivide the imagery use the varibles Polygonize and Sub_img, Sub_image actually closes in on a subset of the image.

## Harvest Monitoring
>The script will now quantify the amount of aggricultural change that is occuring on the image and classify all pixels in the image as either; stagnant, green-up,
>ready for harvest, and recently harvested. All of the images will be compiled into a gif that will inimate the prograssion of harvests over the AOI.
>Next the script will quantify the quantity of havests that have occured and output a animated gif of only the harvests accumulating and an final cumulative image 
>of how many times each field was harvested.



## Additions since Planet
> This code has been converted from the Planet Labs infrastructure and made useable given a remote imagery repository


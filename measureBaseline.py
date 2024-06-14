import sys
import cv2
import numpy
"""
Author: Lucas Vanderheijden

This program is used to measure the baseline value in the camera.py script.
It is only for testing purposes as the output of this script is already hard
coded in camera.py. However, it may need to be rerun if a different camera
of a different quality is used.

This script takes one command line argument, the number of frames to compute
for the test.

The printed output of the script is the average change_val for the number of
frames given as the argument. The idea is to calculate this value when the room is
empty so we get a baseline to check against when trying to detect movement.

This program requires the opencv library
to run. Information can be found at:
https://raspberrypi-guide.github.io/programming/install-opencv.html
"""

if len(sys.argv) != 2:
	print("Usage: <Number of iterations to test>")
	sys.exit(0)

cam = cv2.VideoCapture(0)	# the 0 specifies reading from the first camera

while True:		# get first image
	ret, prev_image = cam.read()		# get image from camera
	if not ret:				# ensure we were successful in grabbing image
		print("Failed to get image, trying again")
		continue
	break

average_val = 0
for i in range(int(sys.argv[1])):
	ret, image = cam.read()		# get image from camera
	if not ret:				# ensure we were successful in grabbing image
		print("Failed to get image, skipping iteration")
		continue
	change_val = int(numpy.sum(numpy.absolute(image-prev_image)))		# compute change_val
	average_val = (average_val*(i) + change_val)/(i+1)	# this formula computes a running average of all the change_val values calculated
	prev_image = image

print("The experimentially determined average value is: ", average_val)		# print the result
cam.release()		# release camera
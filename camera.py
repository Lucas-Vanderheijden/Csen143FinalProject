import time
import sys
import cv2
import numpy
import socket

"""
Author: Lucas Vanderheijden

This program monitors the camera attached to the
raspberry pi and uses sockets to send
the information to the central controller.

This program takes two command line arguments. The first
is the IP address to connect to, the second is the port number.

This program requires the opencv library
to run. Information can be found at:
https://raspberrypi-guide.github.io/programming/install-opencv.html
"""
sensitivity = 5000000	# the change in change_val from baseline value needed to determine there is movement
baseline = 95646774	# the baseline value of change_val that we expect, this value was experimentially determined with the measureBaseline.py script
pause_period = 1	# the time to wait until taking a new frame from the camera
sensor_name = ""	# the name of the sensor, to be taken from user later
image_file_name = ""	# the name of the file where the images taken will be stored. Name will be sensor_name + '.jpg'
data_transmission_block_size = 1024	# the size of the blocks to transmit when sending images

"""
This method takes an address and sends the image
stored in the file with name image_file_name to the specified address (the controller)
"""
def sendImage(addr):
	sock = socket.socket()
	print("Attempting to transmit data")
	sock.connect(address)		# connect to controller
	sock.send(b"cam_update")	# inform controller of connection type
	if(sock.recv(1024) != b'ack'):
		print("Transmission failed, closing connection")
		sock.close()
		return
	else:
		sock.send(sensor_name.encode('utf-8'))		# inform controller which camera is connecting
		if(sock.recv(1024) != b'ack'):
			print("Failed to send name, closing connection")
			sock.close()
			return
		else:
			print("Successfully send name, now sending filename")
			sock.send(image_file_name.encode('utf-8'))
			if(sock.recv(1024) == b'ack'):
				print("Successfully sent file name, now sending data")
				f = open(image_file_name, 'rb')		# open file, specify rb (read binary) because we are reading an image file
				
				# we must transmit the file in blocks as it is too large to send at once
				bytes_read = 1041			# read() is set to read 1024 bytes. But sys.getsizeof(msg) will return 1024 probably because of some overhead in the variable
				while bytes_read == 1041:		# treat 1041 as a magic number that works with block_size 1024, there may be a better way to do this but I'm too tired to find it
					msg = f.read(data_transmission_block_size)		# read the next set of data
					bytes_read = sys.getsizeof(msg)
					print("Bytes read: ", bytes_read)			# for debugging purposes
					sock.send(msg)

					if(sock.recv(1024) != b'ack'):			# make sure nothing goes wrong
						print("Error while transmitting data, closing connection")
						sock.close()
						return
				sock.send(b'EOF')		# tell controller when file has been transmitted

				print("Successfully transmitted file")
				f.close()	# close the file pointer
				sock.close()		# close connection
			else:
				print("Failed to send name, closing connection")
				sock.close()
				return

sock = socket.socket()

if len(sys.argv) < 3:		# the IP addr and port number to connect to must be supplied. Exit if not found
	print("Usage: <IPAddr> <Port #>")
	dht_device.exit()
	sys.exit(0)

address = (sys.argv[1], int(sys.argv[2]))	# store the IPAddr, Port # tuple the socket needs to connect

print("Registering device")
sock.connect(address)	# connect to register device

sock.send(b"cam_reg")		# inform controller device wants to register itself
if sock.recv(1024) != b"ack":		# the controller should respond with acknowledgement
	print("error has occurred in registering device")
	dht_device.exit()
	sys.exit(0)

while True:
	sensor_name = input("Enter the name for the device: ")
	sock.send(sensor_name.encode('utf-8'))

	response = sock.recv(1024)		# store controller response. 'ack' means name checks out. 'name in use' means we must pick a new name
	if response == b"name in use":
		print("Invalid: Name already in use")
	elif response == b"ack":
		print("Name accepted")
		image_file_name = sensor_name + ".jpg"
		break
	else:
		print("Unknown error occurred verifying device name")
		sys.exit(1)

while True:
	associated_temp_sens = input("Enter the name of the temp sensor this camera should be associated with: ")	# ask which temp sensor this camera corresponds to
	sock.send(associated_temp_sens.encode('utf-8'))
	response = sock.recv(1024)
	if response == b'ack':				# ack indicates sensor accepted. sensor not found indicates sensor doesn't exit. sensor in use means sensor already has a camera
		print("Pairing accepted")
		break
	elif response == b'sensor not found':
		print('Temp sensor not found, please input another')
	elif response == b'sensor in use':
		print('Temp sensor already associated with a camera, please input another sensor')
	else:
		print("Unknown error occurred pairing with temp sensor")
		sys.exit(2)

# we have successfully registered the device
sock.close()

cam = cv2.VideoCapture(0)	# the 0 specifies reading from the first camera

while True:
	ret, prevImage = cam.read()	# get the first image
	if not ret:
		print("Failed to get image, trying again")
	else:
		break

while True:
	time.sleep(pause_period)	# wait until sensing again

	ret, image = cam.read()		# get image from camera
	if not ret:				# ensure we were successful in grabbing image
		print("Failed to get image, trying again")
		continue

	change_val = numpy.sum(numpy.absolute(image-prevImage))
	print("Current change_val", change_val)			 # for debugging (helps determine an ideal sensitivity and baseline)
	if change_val > baseline+sensitivity or change_val < baseline-sensitivity:	# only bother sending image when significant change detected indicating something happened
		print("Change detected, sending file. Change value: ", change_val)
		cv2.imwrite(image_file_name, image)		# save image as jpg that we will transfer over
		sendImage(address)

	prevImage = image;

	"""					# uncomment this block to show images pulled from camera (left here for testing purposes)
	cv2.imshow('Imagetest',image)
	k = cv2.waitKey(1)
	if k != -1:
		break
	"""


cam.release()

#cv2.destroyAllWindows()		# uncomment this line if previous block was uncommented as well

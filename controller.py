import socket
import sys
import threading
import cv2
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator
from threading import Event
from PIL import Image
"""
Author: Lucas Vanderheijden

This is the code for the control hub. It receives
data from the thermometers and from the cameras using
sockets. It then uses the data to give commands to the
HVAC system to optimize the temperature for as many people
as possible.

This program takes 1 command line argument which is the port to use

This program requires the YOLOv8 model and its dependancies to run. Information can be
found here: https://docs.ultralytics.com/quickstart/
"""

temp_sens_list = {}	# the dictionary of registered temperature sensor names and their associated temperatures
temp_weight_list = {}	# the dictionary of registered temperature sensor names and the number of people detected in their room
camera_list = {}		# the dictionary of registered cameras and their associated cameras
current_temp = 0	# the weighted average temperature, aka the average temp of each room weighted by the # people dectected in the room
AC_status = 'OFF'		# what we want the AC to be doing
heat_status = 'OFF'		# what we want the heater to be doing
target_temp_file = 'temp.txt'		# file storing the target temperature
newImage = Event()			# used to indicate when a new annotated image must be shown
save_dir = ""		# the directory the annotated images are saved in

# Load a YOLOv8n PyTorch model
model = YOLO("yolov8n.pt")

"""
This function returns the target_temp with the value
stored in the target_temp_file
"""
def update_target_temp():
	f = open(target_temp_file, 'r')		# open the file
	read_msg = f.read()
	print("Read: ", read_msg)
	target_temp = int(read_msg)			# read the value, the file should only have a number which is the target Temp
	f.close()		# close file
	return target_temp

"""
This method handles incoming connections. It is spun off as a new thread
each time a new connection is made.
"""
def onConnection(connected_socket):
	connection_msg = connected_socket.recv(1024)	# first message sent will be update type

	if connection_msg == b"temp_reg":	# if connected device is temp sensor registering itself
		print("Temp sensor trying to register itself")
		connected_socket.send(b'ack')	# tell device to proceed

		while True:
			temperature_handle = connected_socket.recv(1024)	# connected device will then send its preferred name
			print("Trying to register as: ", temperature_handle)

			if temperature_handle not in temp_sens_list:		# if name not in use, accept it
				print("Name not in use, requesting temperature")

				connected_socket.send(b'ack')		# add name to list with initial value and send confirmation
				temp_sens_list[temperature_handle] = float(connected_socket.recv(1024))
				temp_weight_list[temperature_handle] = 0

				print("Registration successful, initial temperature: ", temp_sens_list[temperature_handle])
				break;
			else:
				connected_socket.send(b'name in use')		# if name in use, notify other device and wait for new one
				print("Name already in use, requesting new one")

	elif connection_msg == b"temp_update":		# if connected device is temp sensor with new data
		print("Temp sensor trying to give update")
		connected_socket.send(b'ack')		# tell device to proceed

		temperature_handle = connected_socket.recv(1024)	# get device name
		print("Name of sensor trying to update: ", temperature_handle)

		connected_socket.send(b'ack')		# send confirmation
		temp_sens_list[temperature_handle] = float(connected_socket.recv(1024))		# update temp of that temp sensor
		print("Recieved updated temperature: ", temp_sens_list[temperature_handle])
	
	elif connection_msg == b"cam_reg":	# if connected device is temp sensor registering itself
		print("Camera trying to register itself")
		connected_socket.send(b'ack')	# tell device to proceed

		while True:
			camera_handle = connected_socket.recv(1024)	# connected device will then send its preferred name
			print("Trying to register as: ", camera_handle)

			if camera_handle not in camera_list:		# if name not in use, accept it
				print("Name not in use, requesting associated temp sensor")

				connected_socket.send(b'ack')		# add name to list with initial value and send confirmation
				while True:
					temp_sensor = connected_socket.recv(1024)	# connected device will then send its temp sensor
					if temp_sensor not in temp_sens_list:
						print("Invalid temperature sensor selected. Requesting new one.")
						connected_socket.send(b'sensor not found')
					elif temp_sensor in camera_list.values():
						print("Temperature sensor already in use. Requesting new one.")
						connected_socket.send(b'sensor in use')
					else:
						print("Successfully associated with a temp sensor")
						camera_list[camera_handle] = temp_sensor
						connected_socket.send(b'ack')
						break

				print("Registration of camera successful. Name: ", camera_handle)
				threading.Thread(target = displayImages, args = (camera_handle.decode('utf-8')+'annotated.jpg', )).start()		# spin off another thread to display the input from this camera
				break
			else:
				connected_socket.send(b'name in use')		# if name in use, notify other device and wait for new one
				print("Name already in use, requesting new one")

	elif connection_msg == b"cam_update":
		print("Camera is sending a new frame")
		connected_socket.send(b'ack')

		camera_handle = connected_socket.recv(1024)			# get the handle of the device that is sent
		print("Camera sending frame identified as: ", camera_handle)
		connected_socket.send(b'ack')

		image_file_name = connected_socket.recv(1024).decode(encoding='utf-8')		# get the file name from the device
		print("File name of frame identified as: ", image_file_name)
		connected_socket.send(b'ack')

		f = open(image_file_name, 'wb')
		while True:		# read data from pipe in blocks of 1024 bytes, stop when we reach empty block
			msg = connected_socket.recv(1024)
			if msg == b'EOF':		# check if we have read all data
				break
			f.write(msg)
			connected_socket.send(b'ack')
		print("File recieved and stored")
		f.close()

		results = model.predict(image_file_name, classes = 0)	# run inference on image and only detect people, class 0 is person
		
		im_array = results[0].plot()  # plot a BGR numpy array of predictions
		im = Image.fromarray(im_array[..., ::-1])  # RGB PIL image
		im.save(image_file_name[:len(image_file_name)-4]+"annotated.jpg")  # save image
		newImage.set()			# tell display thread it must update the image

		# haphazard way display image with bounding boxes (for debugging only, this will keep making new windows and never delete them)
		# results[len(results)-1].show(image_file_name)
		
		# get the 'person' class id
		names = model.names
		person_id = list(names)[list(names.values()).index('person')]

		# count the boxes it drew for "person", this is how many people it found in the image
		people_detected = results[0].boxes.cls.tolist().count(person_id)
		print("People detected: ", people_detected)

		# update the list
		temp_sensor = camera_list[camera_handle]
		temp_weight_list[temp_sensor] = people_detected

	elif connection_msg == b'hvac_poll':		# if the connection is hvac control unit asking for an update

		# now that something may have changed, we must compute the current weighted temperature
		total_people = 0;		# the total people detected in all rooms
		for i in temp_weight_list:
			print(temp_weight_list[i])
			total_people += temp_weight_list[i]
		print("The total number of people found is: ", total_people)

		target = update_target_temp()		# make sure our target temperature is updated
		print("Current target temp is: ", target)
		if total_people == 0:		# if there are no people, turn off the heater and AC
			AC_status = 'OFF'
			heat_status = 'OFF'
		else:
			current_temp = 0
			for i in camera_list.values():
				current_temp += temp_sens_list[i]*(temp_weight_list[i]/total_people)
			print("The current weighted temperature is: ", current_temp)

			if current_temp < target:	# update AC and heat commands based on if we need to cool down or heat up
				AC_status = "OFF"
				heat_status = 'ON'
			elif current_temp > target:
				AC_status = "ON"
				heat_status = "OFF"
			else:
				AC_status = 'OFF'
				heat_status = 'OFF'

		print("Sending AC update: ", AC_status)
		connected_socket.send(AC_status.encode('utf-8'))

		if(connected_socket.recv(1024) != b'ack'):
			print("Error in sending AC update, closing connection")
			connected_socket.close()
			return

		print("Sending heater update: ", heat_status)
		connected_socket.send(heat_status.encode('utf-8'))

	connected_socket.close()	# close connection

control_socket = socket.socket()	# create socket to listen for information

if len(sys.argv) < 2:		# if no port specified, use default
	print("Usage: <Port number>")
	sys.exit(0)
else:				# else use specified port
	print("Using specified port: " + sys.argv[1])
	port = int(sys.argv[1])

control_socket.bind(('', port))		# bind socket
control_socket.listen(5)

hostname = socket.gethostname()	# get and print hostname
print(hostname)

IPAddr = socket.gethostbyname(hostname)		# get and print IP address
print(IPAddr)

"""
This method displays the image given by file_name with
the bounding boxes drawn. It is meant to be called in a separate
thread with one thread per camera. It uses the newImage variable to determine
when the image must be updated.
"""
def displayImages(file_name):
	print("Showing image")
	while True:
		if(newImage.is_set()):		# if the image has changed, we need to update it
			newImage.clear()
			annotated_frame = cv2.imread(file_name)		# get the annotated image
			cv2.imshow("Camera", annotated_frame)		# display image

		# Break the loop if 'q' is pressed
		if cv2.waitKey(1) == ord("q"):
			break

while True:
	client_socket, addr = control_socket.accept()	# wait for an update

	print("Connection accepted from: ", addr)
	threading.Thread(target = onConnection, args = (client_socket,)).start()	# spin off a thread to handle connection since more may come in meanwhile
																					# add comma in argument to make it a tuple

socket.close()
cv2.destroyAllWindows()		# destroy the windows
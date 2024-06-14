import adafruit_dht
import time
import board
import socket
import sys
import gpiod

"""
Author: Lucas Vanderheijden

This program monitors the temperature 
of the thermometer attached to the
raspberry pi and uses sockets to send
the information to the central controller.

This program takes two command line arguments. The first
is the IP address to connect to, the second is the port number.

This program requires the adafruit_blinka library
to run. Information can be found at:
https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup
"""

dht_device = adafruit_dht.DHT22(board.D4)	#setup our device. D4 means senor plugged in GPIO pin 4.
pause_period = 2.0		# how long to wait between reading. The DHT 22 sensor should only be polled every 2 sec.
previous_temp = 0		# the temp the last time we checked.


sock = socket.socket()

if len(sys.argv) < 3:		# the IP addr and port number to connect to must be supplied. Exit if not found
	print("Usage: <IPAddr> <Port #>")
	dht_device.exit()
	sys.exit(0)

address = (sys.argv[1], int(sys.argv[2]))	# store the IPAddr, Port # tuple the socket needs to connect

print("Registering device")
sock.connect(address)	# connect to register device

sock.send(b"temp_reg")		# inform controller device wants to register itself
if sock.recv(1024) != b"ack":		# the controller should respond with acknowledgement
	print("error has occurred in registering device")
	dht_device.exit()
	sys.exit(0)

while True:
	sensor_name = input("Enter the name for the device: ")
	sock.send(sensor_name.encode('utf-8'))

	response = sock.recv(1024)		# store controller response. 'ack' means name checks out. 'name in use' means we must pick a new name
	if response == "name in use":
		print("Invalid: Name already in use")
	elif response == b"ack":
		print("Name accepted")
		break
	else:
		print("Unknown error occurred verifying device name")
		dht_device.exit()
		sys.exit(1)

# get initial temperature
while True:
	try:
		temp = dht_device.temperature		# read the temperature
		temp = temp * (9 / 5) + 32		# convert from Celsius to Fahrenheit
		print('Temp={:.1f} F'.format(temp))
		break

	except RuntimeError as error:		# catch and ignore exceptions because the sensor can be finnicky
		print("Sensor error: ", error.args[0])

print("Attempting to send current temperature: ", temp)
sock.send(str(temp).encode('utf-8'))		# send the initial temperature. We must encode it into a byte-string to be send over socket
print("Device successfully registered")
sock.close()		# close connection
# we are now done registering the device

while True:
	time.sleep(pause_period)	# wait until sensing again

	try:
		temp = dht_device.temperature		# read the temperature
		temp = temp * (9 / 5) + 32		# convert from Celsius to Fahrenheit
		print('Temp={:.1f} F'.format(temp))

	except RuntimeError as error:		# catch and ignore exceptions because the sensor can be finnicky
		print("Sensor error: ", error.args[0])

	if not previous_temp == temp:	# if the temperature has changed, send the new one to central hub
		print("Attempting to send temperature update")
		sock = socket.socket()
		sock.connect(address)		# connect to controller

		sock.send(b"temp_update")	# inform controller this is an update message
		if sock.recv(1024) == b"ack":
			sock.send(sensor_name.encode('utf-8'))		# tell controller which device this is
			if sock.recv(1024) == b"ack":
				sock.send(str(temp).encode('utf-8'))		# sent the temperature
				print("Successfully updated temperature to: ", temp)
			else:
				print("An error in sending the temperature update has occurred.")
		else:
			print("An error in sending the temperature update has occurred.")
		sock.close()

		previous_temp = temp	# update the previous temperature
import socket
import sys
import time
import gpiod
"""
Author: Lucas Vanderheijden

This script is for controlling the heater and AC. It sits periodically polls the controller for updates
its status. Turning on and off the AC and Heater is simulated by using
GPIO pins connected to transistors that controll current flow to the LEDs.
It takes two command line arguments which are the ipaddress of controller and port number to use
"""

AC_status = b'OFF'		# the status of the AC, in byte string because that is what we get from the socket connections
heat_status = b'OFF'		# the status of the heater, in byte string because that is what we get from the socket connections
AC_PIN = 14		# the gpiod pin of the AC led
HEAT_PIN = 15		# the gpiod pin of the heater led
pause_period = 1.0	# how long to wait in between polling the controller

AC_line = None	# these variables will store the objects needed to control the GPIO pins later
heat_line = None

if(len(sys.argv) < 3):		# make sure a port number was entered
	print("Usage: <Controller IP addr> <Controller Port Number>")
	sys.exit(0)
address = (sys.argv[1], int(sys.argv[2]))

chip = gpiod.Chip('gpiochip4')		# tells raspberry pi where to find the GPIO pin
AC_line = chip.get_line(AC_PIN)
AC_line.request(consumer="LED", type=gpiod.LINE_REQ_DIR_OUT)	# set LED (the transistor controlling it really) as output

heat_line = chip.get_line(HEAT_PIN)
heat_line.request(consumer="LED", type=gpiod.LINE_REQ_DIR_OUT)	# set LED (the transistor controlling it really) as output

AC_line.set_value(0)	# turn off current flow	to AC led
heat_line.set_value(0)	# turn off current flow to heat led

while True:
	time.sleep(pause_period)	# wait to poll

	sock = socket.socket()
	sock.connect(address)	# connect
	sock.send(b'hvac_poll')		# send request type

	AC_status = sock.recv(1024)		# controller will first send AC status
	if(AC_status == b'ON' or AC_status == b'OFF'):		# check the status was received correctly
		print("Recieved AC status: ", AC_status)
		sock.send(b'ack')
	else:
		print("Did not recieve proper AC status, closing connection")
		sock.send(b'Could not make sense of transmission')
		sock.close()
		continue
	heat_status = sock.recv(1024)		# controller will then send the heater update
	if(heat_status == b'ON' or heat_status == b'OFF'):		# check it makes sense
		print("Recieved heat status: ", heat_status)
		sock.send(b'ack')
	else:
		print("Did not recieve proper heat status, closing connection")
		sock.close()
		continue
	sock.close()	# close connection

	# update the heat and AC based on the new commands
	if(AC_status == b'OFF'):
		AC_line.set_value(0)	# turn off current flow	to AC led
	else:
		AC_line.set_value(1)	# turn on current flow	to AC led

	if(heat_status == b'OFF'):
		heat_line.set_value(0)	# turn off current flow to heat led
	else:
		heat_line.set_value(1)	# turn on current flow to heat led
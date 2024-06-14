"""
Author: Lucas Vanderheijden

This file just gives an easier way to update the target temperature
file controller.py uses to get the target temperature.

It acts as a sort of UI allowing the user to set the target temperature
"""

target_temp_file = 'temp.txt'		# file storing the target temperature

while True:
	target_temp = input("Enter the desired temperature (in Fahrenheit). Enter 'quit' to quit: ")		# get the new temperature
	if target_temp == 'quit':		# quit if told to
		break
	f = open(target_temp_file, 'w')
	f.write(target_temp)		# update target temperature
	f.close()
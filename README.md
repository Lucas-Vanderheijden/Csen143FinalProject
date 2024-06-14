This project contains the code for my Csen143 final project needed to create a smart thermostat
system that can count the number of people in each room and attempt to create the best temperature
for as many people as possible.

To setup:
The controller.py script can be run on just about any computer connected to the internet.
The temperature.py script requires a raspberry pi with a DHT 22 temperature and humidity sensor connected to GPIO pin 4
The camera.py and measureBaseline.py scripts needs a raspberry pi with a USB webcam plugged into any port
The hvacControl.py script needs a raspberry pi with a transtor controlling the an LED connected GPIO pins 14 and 15

The controller.py script needs the YOLOv8 neural network and its dependencies (pytorch, etc.) installed to run. Information can be
found here: https://docs.ultralytics.com/quickstart/

The temperature.py script requires the adafruit_blinka library to run. Information can be found at:
https://learn.adafruit.com/dht-humidity-sensing-on-raspberry-pi-with-gdocs-logging/python-setup

The camera.py script requires the opencv library to run. Information can be found at:
https://raspberrypi-guide.github.io/programming/install-opencv.html

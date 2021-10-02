# ![PYOBD](/pyobd.gif) PYOBD 

This is the remake of the program PYOBD. It works on Python3 and all new libraries. It was tested on Linux, Windows, and it should work on MAC too. You just need an ELM327 USB or bluetooth device.

NOTE: On Windows you will need a suitable driver for your ELM327 device(on Linux it is not needed).

> pyOBD (aka pyOBD-II or pyOBD2) is an OBD-II compliant car diagnostic tool. It is designed to interface with low-cost ELM 32x OBD-II diagnostic interfaces such as ELM327. It will basically allow you to talk to your car's ECU,... display fault codes, display measured values, read status tests, etc. All cars made since 1996 (in the US) or 2001 (in the EU) must be OBD-II compliant, i.e. they should work with pyOBD.

### Video presentation on YouTube(click on it):
[![PYOBD Youtube video 2021](https://img.youtube.com/vi/JxMh_gkUa7Q/0.jpg)](https://www.youtube.com/watch?v=JxMh_gkUa7Q)

On Debian 10 type these commands to install the requirements:

> sudo apt-get install dpkg-dev build-essential libjpeg-dev libtiff-dev libsdl1.2-dev libgstreamer-plugins-base1.0 libnotify-dev freeglut3 freeglut3-dev libsm-dev libgtk-3-dev libwebkit2gtk-4.0-dev libxtst-dev

> pip3 install wxpython==4.1.1

> pip3 install pyserial==3.5

> pip3 install obd==0.7.1

The program is run by typing: 
> python3 pyobd.py

The ignition must be on, to connect to it and display data(key turned one level before engine start). Although most of the sensors are visible only when the engine is running.

The program works nice and I will also add new functionalities to it.

![ELM327](/elm327.jpg)

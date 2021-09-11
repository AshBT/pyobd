This is my port of program pyobd to Python3. It also works on all new libraries. It was tested on Debian 10 (Buster) on USB ELM327 1.3. You don't need any drivers for it in Linux, but you need Pyserial and WXPython.

It was tested on Debian 10, Pyserial (3.4 and 3.5), WXPython 4.1.1.

On Debian 10 type these commands to install the requirements:
sudo apt-get install dpkg-dev build-essential libjpeg-dev libtiff-dev libsdl1.2-dev libgstreamer-plugins-base1.0 libnotify-dev freeglut3 freeglut3-dev libsm-dev libgtk-3-dev libwebkit2gtk-4.0-dev libxtst-dev
pip3 install wxpython=4.1.1
pip3 install pyserial

The program is run by typing "python3 pyobd".

This is a work in progress, I will support it, do bugfixes, test it on Windows 10 also, and add new functionalities.

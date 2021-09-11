#!/usr/bin/env python
###########################################################################
# odb_io.py
# 
# Copyright 2004 Donour Sizemore (donour@uchicago.edu)
# Copyright 2009 Secons Ltd. (www.obdtester.com)
# Copyright 2021 Jure Poljsak (https://github.com/barracuda-fsh/pyobd)
#
# This file is part of pyOBD.
#
# pyOBD is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pyOBD is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyOBD; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
###########################################################################

from pdb import set_trace as bp
import serial
import string
import time
from math import ceil
import wx #due to debugEvent messaging

import re

import obd_sensors

from obd_sensors import hex_to_int

GET_DTC_COMMAND   = "03"
CLEAR_DTC_COMMAND = "04"
GET_FREEZE_DTC_COMMAND = "07"
import traceback
from debugEvent import *
import logging
logger = logging.getLogger(__name__)

#__________________________________________________________________________
def decrypt_dtc_code(code):
    """Returns the 5-digit DTC code from hex encoding"""
    dtc = []
    current = code
    for i in range(0,3):
        if len(current)<4:
            raise "Tried to decode bad DTC: %s" % code

        tc = obd_sensors.hex_to_int(current[0]) #typecode
        tc = tc >> 2
        if   tc == 0:
            type = "P"
        elif tc == 1:
            type = "C"
        elif tc == 2:
            type = "B"
        elif tc == 3:
            type = "U"
        else:
            raise tc

        dig1 = str(obd_sensors.hex_to_int(current[0]) & 3)
        dig2 = str(obd_sensors.hex_to_int(current[1]))
        dig3 = str(obd_sensors.hex_to_int(current[2]))
        dig4 = str(obd_sensors.hex_to_int(current[3]))
        dtc.append(type+dig1+dig2+dig3+dig4)
        current = current[4:]
    return dtc
#__________________________________________________________________________

class OBDPort:
    """ OBDPort abstracts all communication with OBD-II device."""
    _TRY_BAUDS = [38400, 9600, 230400, 115200, 57600, 19200]
    ELM_PROMPT = b'>'
    ELM_LP_ACTIVE = b'OK'
    def __init__(self,portnum,_notify_window,SERTIMEOUT,RECONNATTEMPTS):
        """Initializes port by resetting device and gettings supported PIDs. """
        # These should really be set by the user.
        #baud     = 9600
        baud     = None
        baudrate = baud
        self.baud = baud
        databits = 8
        par      = serial.PARITY_NONE  # parity
        sb       = 1                   # stop bits
        to       = 5#SERTIMEOUT
        self.port_name = portnum
        self.timeout = to
        self.ELMver = "Unknown"
        self.State = 1 #state SERIAL is 1 connected, 0 disconnected (connection failed)
        
        self._notify_window=_notify_window
        wx.PostEvent(self._notify_window, DebugEvent([1,"Opening interface (serial port)"]))                

        try:
            #self.port = serial.Serial(portnum,baud, parity = par, stopbits = sb, bytesize = databits,timeout = to)
            self.port = serial.serial_for_url(portnum, parity=par, stopbits=sb, bytesize=databits, timeout=to)
            print('Port set to '+portnum)
        except serial.SerialException as e:
            self.State = 0
            logger.error(str(e))
            return None
        except OSError as e:
            logger.error(str(e))
            return None
        
        print('Setting auto baud rate')
        if not self.set_baudrate(baudrate):
            logger.error("Failed to set baudrate")
            wx.PostEvent(self._notify_window, DebugEvent([1,"Failed to set baudrate"]))
            return
        
        wx.PostEvent(self._notify_window, DebugEvent([1,"Interface successfully " + self.port.portstr + " opened"]))
        wx.PostEvent(self._notify_window, DebugEvent([1,"Connecting to ECU..."]))
         
        count=0
        while 1: #until error is returned try to connect
            try:
                self.send_command("ATZ")   # initialize
            except serial.SerialException:
                print('atz failed')
                self.State = 0
                return None
            self.ELMver = self.get_result()[-1]
            print('ELM version '+self.ELMver)
            wx.PostEvent(self._notify_window, DebugEvent([2,"atz response:" + self.ELMver]))
            #print(self.get_result())
            
            self.send_command("ATE0")
            time.sleep(1)
            print(self.get_result()[-1])
            #self.send_command("ATH1")
            #time.sleep(1)
            #print(self.get_result())
            #self.send_command("ATL0")
            #time.sleep(1)
            #print(self.get_result())
            #self.send_command("AT RV")
            #time.sleep(1)
            #print(self.get_result())
            #time.sleep(1)
            #self.send_command("ATSP0")
            #time.sleep(1)
            #print(self.get_result())
            self.send_command("0100")
            time.sleep(1)
            ready = self.get_result()[-1]
            print(self.hex_to_bitstring(ready))
            print(ready)
            wx.PostEvent(self._notify_window, DebugEvent([2, "0100 response2:" + ready]))
            self.State = 1
            #return None
            if "41 00" in ready:
                self.State = 1
                wx.PostEvent(self._notify_window, DebugEvent([2, "Connection succeeded!"]))
                return None
            #elif "41 00 FE 3F B8 11" in ready:
            #    self.State = 1
            #    return None
            #elif '86 F1 11 41 00 FE 3F B8 11 CF' in ready:
            #    self.State = 1
            #    return None
            else:
                ready=ready[-5:] #Expecting error message: BUSINIT:.ERROR (parse last 5 chars)
                wx.PostEvent(self._notify_window, DebugEvent([2, "Connection attempt failed:" + ready]))
                time.sleep(5)
                if count == RECONNATTEMPTS:
                    self.close()
                    self.State = 0
                    return None
                wx.PostEvent(self._notify_window, DebugEvent([2, "Connection attempt:" + str(count)]))
                count = count + 1
                #print(self.get_result())
            #bp()
            #wx.PostEvent(self._notify_window, DebugEvent([2,"ate0 response:" + self.get_result()]))
            #print('PreSend command 0100.')
            #self.send_command("0100")
            #print('Sent command 0100.')
            ##self.send_command(b"\x01\x00")
            #self.get_result()
            #print('ready '+self.get_result())
            #ready = self.get_result()
            #print('ready '+self.get_result())
            #print('ready '+self.get_result())
            #print('ready '+self.get_result())
            #print('ready '+self.get_result())
            #wx.PostEvent(self._notify_window, DebugEvent([2,"0100 response1:" + ready]))
            """
            return None
            if ready=="BUSINIT: ...OK":
                ready=self.get_result()
                wx.PostEvent(self._notify_window, DebugEvent([2,"0100 response2:" + ready]))
                return None
            else:             
                #ready=ready[-5:] #Expecting error message: BUSINIT:.ERROR (parse last 5 chars)
                wx.PostEvent(self._notify_window, DebugEvent([2,"Connection attempt failed:" + ready]))
                time.sleep(5)
                if count==RECONNATTEMPTS:
                    self.close()
                    self.State = 0
                    return None
                wx.PostEvent(self._notify_window, DebugEvent([2,"Connection attempt:" + str(count)]))
                count=count+1          
            """

    def hex_to_bitstring(self, str):
        bitstring = ""
        for i in str:
            # silly type safety, we don't want to eval random stuff
            if type(i) == type(''):
                v = eval("0x%s" % i)
                if v & 8:
                    bitstring += '1'
                else:
                    bitstring += '0'
                if v & 4:
                    bitstring += '1'
                else:
                    bitstring += '0'
                if v & 2:
                    bitstring += '1'
                else:
                    bitstring += '0'
                if v & 1:
                    bitstring += '1'
                else:
                    bitstring += '0'
        return bitstring
    def __isok(self, lines, expectEcho=False):
        if not lines:
            return False
        if expectEcho:
            # don't test for the echo itself
            # allow the adapter to already have echo disabled
            return self.__has_message(lines, 'OK')
        else:
            return len(lines) == 1 and lines[0] == 'OK'

    def __has_message(self, lines, text):
        for line in lines:
            if text in line:
                return True
        return False
    
    def set_baudrate(self, baud):
        if baud is None:
            # when connecting to pseudo terminal, don't bother with auto baud
            if self.port_name.startswith("/dev/pts"):
                logger.debug("Detected pseudo terminal, skipping baudrate setup")
                return True
            else:
                return self.auto_baudrate()
        else:
            self.port.baudrate = baud
            return True

    def auto_baudrate(self):
        """
        Detect the baud rate at which a connected ELM32x interface is operating.
        Returns boolean for success.
        """
        # before we change the timout, save the "normal" value
        timeout = self.port.timeout
        self.port.timeout = self.timeout  # we're only talking with the ELM, so things should go quickly
        
        for baud in self._TRY_BAUDS:
            print ('Setting baud rate to '+str(baud))
            self.port.baudrate = baud
            self.port.flushInput()
            self.port.flushOutput()
            # Send a nonsense command to get a prompt back from the scanner
            # (an empty command runs the risk of repeating a dangerous command)
            # The first character might get eaten if the interface was busy,
            # so write a second one (again so that the lone CR doesn't repeat
            # the previous command)
            # All commands should be terminated with carriage return according
            # to ELM327 and STN11XX specifications
            self.port.write(b"\x7F\x7F\r")
            self.port.flush()
            response = self.port.read(1024)
            logger.debug("Response from baud %d: %s" % (baud, repr(response)))
            print ("Response from baud %d: %s" % (baud, repr(response)))
            # watch for the prompt character
            time.sleep(1)
            if response.endswith(b">"):
                print ("Choosing baud %d" % baud)
                logger.debug("Choosing baud %d" % baud)
                self.port.baudrate = baud
                self.port.timeout = timeout  # reinstate our original timeout
                return True

        logger.debug("Failed to choose baud")
        self.port.timeout = timeout  # reinstate our original timeout
        return False

    def close(self):
        """ Resets device and closes all associated filehandles"""
        try:
            self.port
        except:
            return
        if (self.port!= None) and self.State==1:
           self.send_command("atz")
           self.port.close()
        self.port = None
        self.ELMver = "Unknown"

    def send_command(self, cmd):
        """Internal use only: not a public interface"""
        if self.port:
            try:
                #self.port.flushOutput()
                self.port.flushInput()
                cmd = cmd.encode()+b"\r"
                self.port.write(cmd)
                self.port.flush()
                wx.PostEvent(self._notify_window, DebugEvent([3,"Send command:" + str(cmd)]))
            except Exception:
                traceback.print_exc()
                self.__port.close()
                self.__port = None
                wx.PostEvent(self._notify_window, DebugEvent([3, "Device disconnected while writing"]))
                logger.critical("Device disconnected while writing")
                return

    def interpret_result(self,code):
         code = code[0]
         """Internal use only: not a public interface"""
         # Code will be the string returned from the device.
         # It should look something like this:
         # '41 11 0 0\r\r'
         
         # 9 seems to be the length of the shortest valid response
         if len(code) < 7:
             #raise "BogusCode"
             print ('BogusCode')
             pass
         
         # get the first thing returned, echo should be off
         code = str.split(code, "\r")
         code = code[0]
         
         #remove whitespace
         code = code.replace(' ', '')
         ##code = str.split(code)
         ##code = str.join(code, "")
         
         #cables can behave differently 
         if code[:6] == "NODATA": # there is no such sensor
             return "NODATA"
             
         # first 4 characters are code from ELM
         code = code[4:]
         return code
    
    def get_result(self):
        """Internal use only: not a public interface"""
        #delay = 0.2
        #time.sleep(delay)

        buffer = bytearray()

        while True:
            # retrieve as much data as possible
            try:
                data = self.port.read(self.port.in_waiting or 1)
            except Exception:
                self.State = 0
                self.port.close()
                self.port = None
                print("Device disconnected while reading")
                return []

            # if nothing was received
            if not data:
                print("Failed to read port")
                break

            buffer.extend(data)

            # end on chevron (ELM prompt character) or an 'OK' which
            # indicates we are entering low power state
            if self.ELM_PROMPT in buffer or self.ELM_LP_ACTIVE in buffer:
                break

        # log, and remove the "bytearray(   ...   )" part
        print("read: " + repr(buffer)[10:-1])

        # clean out any null characters
        buffer = re.sub(b"\x00", b"", buffer)

        # remove the prompt character
        if buffer.endswith(self.ELM_PROMPT):
            buffer = buffer[:-1]

        # convert bytes into a standard string
        string = buffer.decode("utf-8", "ignore")

        # splits into lines while removing empty lines and trailing spaces
        lines = [s.strip() for s in re.split("[\r\n]", string) if bool(s)]
        if len(lines) <=0:
            print("no response; wait: 1 seconds")
            time.sleep(1)

            ### COPIED
            buffer = bytearray()
            while True:
                # retrieve as much data as possible
                try:
                    data = self.port.read(self.port.in_waiting or 1)
                except Exception:
                    self.State = 0
                    self.port.close()
                    self.port = None
                    print("Device disconnected while reading")
                    return []

                # if nothing was received
                if not data:
                    print("Failed to read port")
                    break

                buffer.extend(data)

                # end on chevron (ELM prompt character) or an 'OK' which
                # indicates we are entering low power state
                if self.ELM_PROMPT in buffer or self.ELM_LP_ACTIVE in buffer:
                    break

            # log, and remove the "bytearray(   ...   )" part
            print("read: " + repr(buffer)[10:-1])

            # clean out any null characters
            buffer = re.sub(b"\x00", b"", buffer)

            # remove the prompt character
            if buffer.endswith(self.ELM_PROMPT):
                buffer = buffer[:-1]

            # convert bytes into a standard string
            string = buffer.decode("utf-8", "ignore")

            # splits into lines while removing empty lines and trailing spaces
            lines = [s.strip() for s in re.split("[\r\n]", string) if bool(s)]
            ### COPIED

        return lines

        """
        buff = b""
        if self.port:
            while 1:
                c = self.port.read()
                
                #print('Got: '+str(c))
                if c == b'\r' and len(buff) > 0:
                    break
                else:
                    if buff != b"" or c != b">": #if something is in buffer, add everything
                        buff+=c
            buff = buff.decode('utf-8', 'ignore')
            #wx.PostEvent(self._notify_window, DebugEvent([3,"Get result:" + buff]))
            #print ('Returning buffer: ' + buff)
            return buff
        else:
            wx.PostEvent(self._notify_window, DebugEvent([3,"NO self.port!" + str(buff)]))
        return None
        """

     # get sensor value from command
    def get_sensor_value(self,sensor):
         """Internal use only: not a public interface"""
         cmd = sensor.cmd
         self.send_command(cmd)
         data = self.get_result()
         
         if data:
             data = self.interpret_result(data)
             if data != "NODATA":
                 data = sensor.value(data)
         else:
             return "NORESPONSE"
         return data

     # return string of sensor name and value from sensor index
    def sensor(self , sensor_index):
        """Returns 3-tuple of given sensors. 3-tuple consists of
         (Sensor Name (string), Sensor Value (string), Sensor Unit (string) ) """
        sensor = obd_sensors.SENSORS[sensor_index]
        r = self.get_sensor_value(sensor)
        return (sensor.name,r, sensor.unit)

    def sensor_names(self):
        """Internal use only: not a public interface"""
        names = []
        for s in obd_sensors.SENSORS:
            names.append(s.name)
        return names
         
    def get_tests_MIL(self):
        statusText=["Unsupported","Supported - Completed","Unsupported","Supported - Incompleted"]
         
        statusRes = self.sensor(1)[1] #GET values
        statusTrans = [] #translate values to text
         
        statusTrans.append(str(statusRes[0])) #DTCs
         
        if statusRes[1]==0: #MIL
            statusTrans.append("Off")
        else:
            statusTrans.append("On")
            
        for i in range(2,len(statusRes)): #Tests
            #print(statusRes[i])
            statusTrans.append(statusText[statusRes[i]]) 
         
        return statusTrans
          
     #
     # fixme: j1979 specifies that the program should poll until the number
     # of returned DTCs matches the number indicated by a call to PID 01
     #
    def get_dtc(self):
        """Returns a list of all pending DTC codes. Each element consists of
        a 2-tuple: (DTC code (string), Code description (string) )"""
        dtcLetters = ["P", "C", "B", "U"]
        r = self.sensor(1)[1] #data
        dtcNumber = r[0]
        mil = r[1]
        DTCCodes = []
          
          
        print ("Number of stored DTC:" + str(dtcNumber) + " MIL: " + str(mil))
        # get all DTC, 3 per mesg response
        res = ''  # ADDED BY JURE
        for i in range(0, int((dtcNumber+2)/3)):    # ADDED BY JURE int()
            self.send_command(GET_DTC_COMMAND)
            res = self.get_result()
            print ("DTC result:" + res)
            for i in range(0, 3):
                val1 = hex_to_int(res[3+i*6:5+i*6])
                val2 = hex_to_int(res[6+i*6:8+i*6]) #get DTC codes from response (3 DTC each 2 bytes)
                val  = (val1<<8)+val2 #DTC val as int
                
                if val==0: #skip fill of last packet
                  break
                   
                DTCStr=dtcLetters[(val&0xC000)>14]+str((val&0x3000)>>12)+str(val&0x0fff) 
                
                DTCCodes.append(["Active",DTCStr])
          
            #read mode 7
            self.send_command(GET_FREEZE_DTC_COMMAND)
            res = self.get_result()
          
            if res[:7] == "NO DATA": #no freeze frame
                return DTCCodes
        if res == '':  # ADDED BY JURE
            return DTCCodes  # ADDED BY JURE
        print ("DTC freeze result:" + res)
        for i in range(0, 3):
            val1 = hex_to_int(res[3+i*6:5+i*6])
            val2 = hex_to_int(res[6+i*6:8+i*6]) #get DTC codes from response (3 DTC each 2 bytes)
            val  = (val1<<8)+val2 #DTC val as int
                
            if val==0: #skip fill of last packet
                break
                   
            DTCStr=dtcLetters[(val&0xC000)>14]+str((val&0x3000)>>12)+str(val&0x0fff)
            DTCCodes.append(["Passive",DTCStr])
              
        return DTCCodes
              
    def clear_dtc(self):
        """Clears all DTCs and freeze frame data"""
        self.send_command(CLEAR_DTC_COMMAND)     
        r = self.get_result()
        return r
     
    def log(self, sensor_index, filename): 
        file = open(filename, "w")
        start_time = time.time() 
        if file:
            data = self.sensor(sensor_index)
            file.write("%s     \t%s(%s)\n" % \
                         ("Time", string.strip(data[0]), data[2])) 
            while 1:
                now = time.time()
                data = self.sensor(sensor_index)
                line = "%.6f,\t%s\n" % (now - start_time, data[1])
                file.write(line)
                file.flush()
          

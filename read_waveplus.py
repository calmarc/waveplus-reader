# MIT License
#
# Copyright (c) 2018 Airthings AS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# https://airthings.com

# ===============================
# Module import dependencies
# ===============================
#
#


from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate
import sys
import time
import datetime
import struct
import tableprint

bash_red='\033[0;31m'
bash_black='\033[0;30m'
bash_dark_gray='\033[1;30m'
bash_red='\033[0;31m'
bash_light_red='\033[1;31m'
bash_green='\033[0;32m'
bash_light_green='\033[1;32m'
bash_brown_orange='\033[0;33m'
bash_yellow='\033[1;33m'
bash_blue='\033[0;34m'
bash_light_blue='\033[1;34m'
bash_purple='\033[0;35m'
bash_light_purple='\033[1;35m'
bash_cyan='\033[0;36m'
bash_light_cyan='\033[1;36m'
bash_light_gray='\033[0;37m'
bash_white='\033[1;37m'
bash_nc='\033[0m' # No Color

# ===============================
# Script guards for correct usage
# ===============================

if len(sys.argv) < 3:
    print ("ERROR: Missing input argument SN or SAMPLE-PERIOD.")
    print ("USAGE: read_waveplus.py SN SAMPLE-PERIOD [pipe > yourfile.txt]")
    print ("    where SN is the 10-digit serial number found under the magnetic backplate of your Wave Plus.")
    print ("    where SAMPLE-PERIOD is the time in seconds between reading the current values.")
    print ("    where [pipe > yourfile.txt] is optional and specifies that you want to pipe your results to yourfile.txt.")
    sys.exit(1)

if sys.argv[1].isdigit() is not True or len(sys.argv[1]) != 10:
    print ("ERROR: Invalid SN format.")
    print ("USAGE: read_waveplus.py SN SAMPLE-PERIOD [pipe > yourfile.txt]")
    print ("    where SN is the 10-digit serial number found under the magnetic backplate of your Wave Plus.")
    print ("    where SAMPLE-PERIOD is the time in seconds between reading the current values.")
    print ("    where [pipe > yourfile.txt] is optional and specifies that you want to pipe your results to yourfile.txt.")
    sys.exit(1)

if sys.argv[2].isdigit() is not True or int(sys.argv[2])<0:
    print ("ERROR: Invalid SAMPLE-PERIOD. Must be a numerical value larger than zero.")
    print ("USAGE: read_waveplus.py SN SAMPLE-PERIOD [pipe > yourfile.txt]")
    print ("    where SN is the 10-digit serial number found under the magnetic backplate of your Wave Plus.")
    print ("    where SAMPLE-PERIOD is the time in seconds between reading the current values.")
    print ("    where [pipe > yourfile.txt] is optional and specifies that you want to pipe your results to yourfile.txt.")
    sys.exit(1)

if len(sys.argv) > 3:
    Mode = sys.argv[3].lower()
else:
    Mode = 'terminal' # (default) print to terminal 

if Mode!='pipe' and Mode!='terminal':
    print ("ERROR: Invalid piping method.")
    print ("USAGE: read_waveplus.py SN SAMPLE-PERIOD [pipe > yourfile.txt]")
    print ("    where SN is the 10-digit serial number found under the magnetic backplate of your Wave Plus.")
    print ("    where SAMPLE-PERIOD is the time in seconds between reading the current values.")
    print ("    where [pipe > yourfile.txt] is optional and specifies that you want to pipe your results to yourfile.txt.")
    sys.exit(1)

SerialNumber = int(sys.argv[1])
SamplePeriod = int(sys.argv[2])

# ====================================
# Utility functions for WavePlus class
# ====================================

def parseSerialNumber(ManuDataHexStr):
    if (ManuDataHexStr == None or ManuDataHexStr == "None"):
        SN = "Unknown"
    else:
        ManuData = bytearray.fromhex(ManuDataHexStr)

        if (((ManuData[1] << 8) | ManuData[0]) == 0x0334):
            SN  =  ManuData[2]
            SN |= (ManuData[3] << 8)
            SN |= (ManuData[4] << 16)
            SN |= (ManuData[5] << 24)
        else:
            SN = "Unknown"
    return SN

# ===============================
# Class WavePlus
# ===============================

class WavePlus():

    def __init__(self, SerialNumber):
        self.periph        = None
        self.curr_val_char = None
        self.MacAddr       = None
        self.SN            = SerialNumber
        self.uuid          = UUID("b42e2a68-ade7-11e4-89d3-123b93f75cba")

    def connect(self):
        # Auto-discover device on first connection
        if (self.MacAddr is None):
            scanner     = Scanner().withDelegate(DefaultDelegate())
            searchCount = 0
            while self.MacAddr is None and searchCount < 50:
                devices      = scanner.scan(0.1) # 0.1 seconds scan period
                searchCount += 1
                for dev in devices:
                    ManuData = dev.getValueText(255)
                    SN = parseSerialNumber(ManuData)
                    if (SN == self.SN):
                        self.MacAddr = dev.addr # exits the while loop on next conditional check
                        break # exit for loop
            
            if (self.MacAddr is None):
                print ("ERROR: Could not find device.")
                print ("GUIDE: (1) Please verify the serial number.")
                print ("       (2) Ensure that the device is advertising.")
                print ("       (3) Retry connection.")
                sys.exit(1)
        
        # Connect to device
        if (self.periph is None):
            self.periph = Peripheral(self.MacAddr)
        if (self.curr_val_char is None):
            self.curr_val_char = self.periph.getCharacteristics(uuid=self.uuid)[0]
        
    def read(self):
        if (self.curr_val_char is None):
            print ("ERROR: Devices are not connected.")
            sys.exit(1)            
        #print (self.periph.getServices())
        #print (self.periph.getCharacteristics())
        #print (self.periph.getDescriptors())
        rawdata = self.curr_val_char.read()
        rawdata = struct.unpack('<BBBBHHHHHHHH', rawdata)
        sensors = Sensors()
        sensors.set(rawdata)
        return sensors
    
    def disconnect(self):
        if self.periph is not None:
            self.periph.disconnect()
            self.periph = None
            self.curr_val_char = None

# ===================================
# Class Sensor and sensor definitions
# ===================================

NUMBER_OF_SENSORS               = 7
SENSOR_IDX_HUMIDITY             = 0
SENSOR_IDX_RADON_SHORT_TERM_AVG = 1
SENSOR_IDX_RADON_LONG_TERM_AVG  = 2
SENSOR_IDX_TEMPERATURE          = 3
SENSOR_IDX_REL_ATM_PRESSURE     = 4
SENSOR_IDX_CO2_LVL              = 5
SENSOR_IDX_VOC_LVL              = 6

class Sensors():
    def __init__(self):
        self.sensor_version = None
        self.sensor_data    = [None]*NUMBER_OF_SENSORS
        self.sensor_units   = ["%rH", "Bq/m3", "Bq/m3", "°C", "hPa", "ppm", "ppb"]
    
    def set(self, rawData):
        self.sensor_version = rawData[0]
        if (self.sensor_version == 1):
            self.sensor_data[SENSOR_IDX_HUMIDITY]             = rawData[1]/2.0
            self.sensor_data[SENSOR_IDX_RADON_SHORT_TERM_AVG] = self.conv2radon(rawData[4])
            self.sensor_data[SENSOR_IDX_RADON_LONG_TERM_AVG]  = self.conv2radon(rawData[5])
            self.sensor_data[SENSOR_IDX_TEMPERATURE]          = rawData[6]/100.0
            self.sensor_data[SENSOR_IDX_REL_ATM_PRESSURE]     = rawData[7]/50.0
            self.sensor_data[SENSOR_IDX_CO2_LVL]              = rawData[8]*1.0
            self.sensor_data[SENSOR_IDX_VOC_LVL]              = rawData[9]*1.0
        else:
            print ("ERROR: Unknown sensor version.\n")
            print ("GUIDE: Contact Airthings for support.\n")
            sys.exit(1)
   
    def conv2radon(self, radon_raw):
        radon = "N/A" # Either invalid measurement, or not available
        if 0 <= radon_raw <= 16383:
            radon  = radon_raw
        return radon

    def getValue(self, sensor_index):
        return self.sensor_data[sensor_index]

    def getUnit(self, sensor_index):
        return self.sensor_units[sensor_index]

try:
    #---- Initialize ----#
    waveplus = WavePlus(SerialNumber)
    
    #print ("Device serial number: %s" % SerialNumber)
    
        
    num_retries = 0
    tot_retries = 0
    max_tries = 10
    num_printed = 0

    header = ['         Time ', '    CO2 level ', '    VOC level ', '  Temperature ', '     Humidity ', '     Pressure ', ' Radon ST avg ', ' Radon LT avg ']

    while True:

        # print headers each 12 lines
        if num_printed % 24 == 0:
            
            if (Mode=='terminal'):
                #if tot_retries > 0:
                #    print (tableprint.bottom(8,width=14, style="clean"))
                print (tableprint.header(header, width=14, style="clean"))
            elif (Mode=='pipe'):
                #if tot_retries > 0:
                #    print (tableprint.bottom(8,width=14, style="clean"))
                print (header)

        num_printed = num_printed + 1

        try:
            waveplus.connect()
            num_retries = 0
        except Exception as e:
            err = e
            num_retries = num_retries + 1
            tot_retries = tot_retries + 1

            if num_retries > max_tries:
                raise err
            time.sleep(90)
            continue #go while True
        
        # read values
        sensors = waveplus.read()
        
        # extract
        if num_printed % 24 == 1:
            mytime     = datetime.datetime.now().strftime("(%S) %H:%M ")
        else:
            mytime = datetime.datetime.now().strftime("%H:%M ")

        if tot_retries > 0:
            mytime     = "#" + str(tot_retries) + "  " + mytime
            tot_retries = 0

        CO2_lvl_file = str("{:.0f}".format(sensors.getValue(SENSOR_IDX_CO2_LVL)))
        CO2_lvl      = bash_light_green + CO2_lvl_file + " " + str(sensors.getUnit(SENSOR_IDX_CO2_LVL)) + " " + bash_nc
        VOC_lvl_file = str("{:.0f}".format(sensors.getValue(SENSOR_IDX_VOC_LVL)))
        VOC_lvl      = bash_dark_gray + VOC_lvl_file + " " + str(sensors.getUnit(SENSOR_IDX_VOC_LVL)) + " " + bash_nc
        temperature_file  = str("{:.1f}".format(sensors.getValue(SENSOR_IDX_TEMPERATURE)))
        temperature  = bash_light_red + temperature_file + " " + str(sensors.getUnit(SENSOR_IDX_TEMPERATURE)) + " " + bash_nc
        humidity     = bash_light_cyan + str("{:.1f}".format(sensors.getValue(SENSOR_IDX_HUMIDITY)))  + " " + str(sensors.getUnit(SENSOR_IDX_HUMIDITY)) + " " + bash_nc
        pressure     = bash_brown_orange + str("{:.0f}".format(sensors.getValue(SENSOR_IDX_REL_ATM_PRESSURE)))     + " " + str(sensors.getUnit(SENSOR_IDX_REL_ATM_PRESSURE)) + " " + bash_nc
        radon_st_avg = bash_green + str("{:.0f}".format(sensors.getValue(SENSOR_IDX_RADON_SHORT_TERM_AVG))) + " " + str(sensors.getUnit(SENSOR_IDX_RADON_SHORT_TERM_AVG)) + " " + bash_nc
        radon_lt_avg = bash_green + str("{:.0f}".format(sensors.getValue(SENSOR_IDX_RADON_LONG_TERM_AVG)))  + " " + str(sensors.getUnit(SENSOR_IDX_RADON_LONG_TERM_AVG)) + " " + bash_nc


        # Print data
        data = [mytime, CO2_lvl, VOC_lvl, temperature, humidity, pressure, radon_st_avg, radon_lt_avg]
        if (Mode=='terminal'):
            print (tableprint.row(data, width=14, style="clean"))
            # into file - so dwmstatus can read from it and put it up.
            try:
                with open("/tmp/airthings.tmp.txt", "w") as f:
                    f.write(temperature_file + "°C"  + " CO2:" + CO2_lvl_file + " VOC:" + VOC_lvl_file)
                    f.close
            except:
                pass

        elif (Mode=='pipe'):
            print (data)

        waveplus.disconnect()

        time.sleep(SamplePeriod)

finally:
    waveplus.disconnect()

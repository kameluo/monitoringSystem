# --------------------Introduction---------------------------
# University of Jaen
# Kamel-M.Fuantes-2021
#
# Brief idea about the code:
# This code is created to make a GUI to run the experiments
# and to get the measurments of the current, voltage, temperature and power density.
# in order to run the code make sure that the temperature sensorcable is
# connected to the 3-wire pin on the raspberry-pi, also us should unplug and plug
# again the USB cable of the radiometer if you switch on the raspberry-pi to make 
# it recognised by the operating system
# -----------------------------------------------------------

# Code_root/
#  │
#  ├── Libararies
#  ├── Variables and declarations
#  ├── Functions
#  ├── Main code
# --------------------Libraries------------------------------
# 1) Libraries used for creating the GUI, we used the tkinter library
#    Documentation: https://docs.python.org/3/library/tkinter.html
#    Useful video: https://www.youtube.com/watch?v=yQSEXcf6s2I&list=PLCC34OHNcOtoC6GglhF3ncJ5rLwQrLGnV
from _datetime import datetime
import time
import schedule
from schedule import every, repeat, run_pending #-->https://schedule.readthedocs.io/en/stable/
import sys #-->used to stop the execution of the code when it is finished
			#-->https://pypi.org/project/schedule/

# 3) Libaries used to control the hardware pins of the raspberry-pi
#    Documentation-1: https://circuitpython.readthedocs.io/en/3.x/shared-bindings/busio/__init__.html
#    Documentation-2: https://learn.adafruit.com/arduino-to-circuitpython/the-board-module
#    Documentation-3: https://pypi.org/project/RPi.GPIO/
import busio #--> used to get the value of the sensors connected to the 3-wire GPIO pin, in our case is the temperature sensor
from board import * #-->also used to control the hardware of the board like the previous library and for the communication protocols such as I2C
import RPi.GPIO as GPIO #-->used to gontrol the OUTPUT GPIO pin, in our case is the N-MOSFET,(the OUTPUT voltage of the pin is 3.3V)
import board

# 4) Library used for the Digital current sensor INA219, to get the current passing through the branch and the voltage drop over the load
#    Documentation: https://github.com/adafruit/Adafruit_CircuitPython_INA219
from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219

# 5) Library used to create and insert data to EXCEL files
#    Documentation: https://xlsxwriter.readthedocs.io/
import xlsxwriter as xw

# 6) Library used to make the serial communication with the radiometer
#    Documentation: https://pypi.org/project/pyserial/
import serial, string

# 7) Library used to run the temperature sensor and the radiometers in 2 different cores for the main one(the raspberry-pi has 4 cores)
#    Documentation: https://docs.python.org/3/library/_thread.html
#    Useful video: https://www.youtube.com/watch?v=b8Tf2Nahsfw
import _thread
# 8) Library used to commenicate with the temperature sensor DS18B20 and to change its resolution if needed
#    Documentation: https://github.com/timofurrer/w1thermsensor
from w1thermsensor import W1ThermSensor, Sensor
# --------------------End of libraries---------------------------

# ---------------Variables and declarations----------------------
#
# To check the serial port which the radiometer is connected to the raspberry-pi,
# write in the console screen that command and check:
# python -m serial.tools.miniterm
#
RadioOutput="" #--> declaration for the radiometer OUTPUT value
RadioFlag=True #--> flag to check if the user will use the radiometer in the test or not
testDuration=0 #--> the test duration entered by the user
testIntervals=1 #--> the code will get the measurments every 1 second

i2c_bus = board.I2C() #--> declaration for the i2c bus used to get the data from the current sensor INA219
ina219 = INA219(i2c_bus,0x41) #--> declaration for the object used for the INA219
# optional : change configuration to use 32 samples averaging for both bus voltage and shunt voltage
ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
# optional : change voltage range to 16V
ina219.bus_voltage_range = BusVoltageRange.RANGE_32V


sensor1 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="041770da4dff")#--> declaration for the object used to get the data from the the DS18B20 temperature seonsor
sensor1.set_resolution(10) #--> setting the resolution of the temperature sensor
temperatureThreadOutput=0.0 #--> setting an initial value for the temperature sensor OUTPUT


GPIO.setmode(GPIO.BCM) #--> Preparing the mode used in controlling the GPIO pins of the raspberry-pi
GPIO.setup(13,GPIO.OUT) #--> setting pin 13 as an OUTPUT pin
GPIO.setwarnings(False) #--> setting the warnings off because it is not needed in our application

outputMeasurmentsList=[]#list used to save the measured data

finishFlag=False
excelFileName=""
# -------------End of variables and declarations-------------------

# -------------------------Functions-------------------------------

#
# 1) This function is initating a new thread for the use of the temperature sensor on the second core
# param :Unused.
# return :The OUTPUT value of the temperature sensor
#
def temperatureThread():#core2--->check the thread function down
    global temperatureThreadOutput
    temperatureThreadOutput=sensor1.get_temperature()

#
# 2) This function is initating a new thread for the use of the radiometer sensor on the third core
# param :Unused.
# return :The OUTPUT value of the radiometer sensor
# 
def radioThread():#core3--->check the thread function down
    global RadioOutput
    ser=serial.Serial('/dev/ttyUSB1',115200,8,'N',1,timeout=1)
    ser.write(b'gi\r')
    time.sleep(0.5)#giving the radiometer 0.5 seconds to get the response
    output=ser.readline()
    RadioOutput=str(output,'utf-8')
    ser.flush()
    ser.close()

#
# 3) This function is used if the user wants to save the data in an Excel file
# param :Excel file name, output measurments list.
# return :Unused
#  
def createAndAddDataToExcelFile(excelFileName, outputMeasurmentsList):
    # Createing Excel file
    workbook = xw.Workbook(excelFileName+ "-" + datetime.now().date().strftime("%d-%m-%Y") +".xlsx")
    worksheet1 = workbook.add_worksheet()
    worksheet1.write(0,0,"Time")
    worksheet1.write(0,1,"Intervals")
    worksheet1.write(0,2,"Current")
    worksheet1.write(0,3,"Voltage")
    worksheet1.write(0,4,"Temperature")
    worksheet1.write(0,5,"Power Density W/cm2")
    worksheet1.write(0,6,"Power Density mW/cm2")

    # Inserting data to the Excel file
    existingWorkingSheet = workbook.get_worksheet_by_name("Sheet1")
    itemCounter=0
    while itemCounter < len(outputMeasurmentsList):
        measurmentValue=0
        while measurmentValue < len(outputMeasurmentsList[itemCounter]):
            existingWorkingSheet.write(itemCounter+1, measurmentValue, outputMeasurmentsList[itemCounter][measurmentValue])
            measurmentValue += 1
        itemCounter += 1
    workbook.close() 

#
# 4) This function is used once the user start the test by pressting "Start test" on the GUI
# param :Unused.
# return :Unused
#  
def startButtonFunction():
    global RadioOutput
    global temperatureThreadOutput
    global testDuration
    global finishFlag
    global excelFileName
    global testIntervals

    #startingTestTime=datetime.now()#.replace(microsecond=0)

    GPIO.output(13,GPIO.HIGH)

@repeat(every().second)
def runCode():
	_thread.start_new_thread(temperatureThread, ()) #--> Starting the second thread of by calling the temperature sensor function
	
	#if RadioFlag==True:
	#	_thread.start_new_thread(radioThread, ()) #--> Starting the third thread of by calling the radiometer sensor function, if selected
	  
	_thread.start_new_thread(radioThread, ()) if RadioFlag==True else None

	bus_voltage = ina219.bus_voltage  # voltage on V- (load side)
	shunt_voltage = ina219.shunt_voltage  # voltage between V+ and V- across the shunt
	current = ina219.current  # current in mA
	Voltage = "{:.2f}".format(bus_voltage + shunt_voltage)
	Current = "{:.2f}".format(current)

	outputMeasurmentsList.append([datetime.now().strftime("%I:%M:%S"), len(outputMeasurmentsList), Current, Voltage, temperatureThreadOutput, RadioOutput.replace('\n','').replace('\r','').replace("'","").replace(' ','')])

	if len(outputMeasurmentsList) >= testDuration:
		print("-----------LED off-----------")
		finishFlag=True
		GPIO.setmode(GPIO.BCM) #--> Preparing the mode used in controlling the GPIO pins of the raspberry-pi
		GPIO.setup(13,GPIO.OUT) #--> setting pin 13 as an OUTPUT pin
		GPIO.setwarnings(False) #--> setting the warnings off because it is not needed in our application
		GPIO.output(13,GPIO.LOW)
		GPIO.cleanup()
		createAndAddDataToExcelFile(excelFileName, outputMeasurmentsList)
		outputMeasurmentsList.clear()
		schedule.cancel_job(runCode)
		schedule.clear()
		print("End test")
		sys.exit()

# ----------------------End of functions-------------------------------

############ Main code #############		

while finishFlag==False:


	excelFileName = input("Input the excel file name: ")

	answer = input("Are you going to use the radiometer? yes or no: ") 
	if answer=="no": 
		RadioFlag=False
		RadioOutput="Not-Connected"
	elif answer == "yes":
		RadioFlag=True

	testDuration = int(input("Input the test duration in seconds: "))

	startButtonFunction()
	while finishFlag==False:
		schedule.run_pending() #--> start running the scheduled function every 1 second
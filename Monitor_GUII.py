from tkinter import *
from tkinter import ttk
import tkinter as tk
from tkinter import messagebox
####################
import datetime
import time
import busio
from board import *
####################
import RPi.GPIO as GPIO
import time
import board
from adafruit_ina219 import ADCResolution, BusVoltageRange, INA219
####################
import xlsxwriter as xw
import serial, string, time
####################
import _thread
####################
RadioOutput=""
"""
to check the serial port which the radiometer is connected to,
write in the console screen that command and check:
python -m serial.tools.miniterm
"""


i2c_bus = board.I2C()
ina219 = INA219(i2c_bus,0x41)
# optional : change configuration to use 32 samples averaging for both bus voltage and shunt voltage
ina219.bus_adc_resolution = ADCResolution.ADCRES_12BIT_32S
ina219.shunt_adc_resolution = ADCResolution.ADCRES_12BIT_32S
# optional : change voltage range to 16V
ina219.bus_voltage_range = BusVoltageRange.RANGE_32V


from w1thermsensor import W1ThermSensor, Sensor
sensor1 = W1ThermSensor(sensor_type=Sensor.DS18B20, sensor_id="041770da4dff")
sensor1.set_resolution(10)
temperatureThreadOutput=0.0

GPIO.setmode(GPIO.BCM)
GPIO.setup(13,GPIO.OUT)
GPIO.setwarnings(False)
############ Functions #############
def getCheckAnswerRadiometer():
    if(checkBoxAnswerRadiometer.get()==0):
        RadioState=False
    elif(checkBoxAnswerRadiometer.get()==1):
        RadioState=True

def getCheckAnswerOverTemperature():
    if(checkBoxAnswerTemperature.get()==0):
        maxTemperatureInput.insert(0, "max temperature")
        maxTemperatureInput.configure(state="disabled")
    elif(checkBoxAnswerTemperature.get()==1):
        maxTemperatureInput.configure(state="normal")
        maxTemperatureInput.delete(0,END)

def getCheckAnswerFileName():
    if(checkBoxAnswerFileName.get()==0):
        answerFileName.insert(0, "file name")
        answerFileName.configure(state="disabled")
    elif(checkBoxAnswerFileName.get()==1):
        answerFileName.configure(state="normal")
        answerFileName.delete(0,END)

def temperatureThread():#core2--->check the thread function down
    global temperatureThreadOutput
    temperatureThreadOutput=sensor1.get_temperature()
    
def radioThread():#core3--->check the thread function down
    global RadioOutput
    ser=serial.Serial('/dev/ttyUSB1',115200,8,'N',1,timeout=1)
    ser.write(b'gi\r')
    time.sleep(0.5)
    output=ser.readline()
    RadioOutput=str(output,'utf-8')
    ser.flush()
    ser.close()
    
def startButtonFunction():
    global RadioOutput
    RadioOutput=""
    global temperatureThreadOutput
    temperatureThreadOutput=0.0
    resultTree.delete(*resultTree.get_children())
    testDuration = int(testTimeInput.get()) 
    testIntervals = int(testIntervalsInput.get())
    if (checkBoxAnswerTemperature.get()==1):
        maximumTemperatureWarning=int(maxTemperatureInput.get())
    if(checkBoxAnswerFileName.get()==1):
        excelFileName=answerFileName.get()
    
    startingTestTime=datetime.datetime.now().replace(microsecond=0)
    treeIntervalCounter=0
        
    if(checkBoxAnswerFileName.get()==1):
        workbook = xw.Workbook(answerFileName.get() + "-" + datetime.datetime.now().date().strftime("%d-%m-%Y") +".xlsx")
        worksheet1 = workbook.add_worksheet()
        worksheet1.write(0,0,"Time")
        worksheet1.write(0,1,"Intervals")
        worksheet1.write(0,2,"Current")
        worksheet1.write(0,3,"Voltage")
        worksheet1.write(0,4,"Temperature")
        worksheet1.write(0,5,"Power Density W/cm2")
        worksheet1.write(0,6,"Power Density mW/cm2")
        #workbook.close()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(13,GPIO.OUT)
    GPIO.setwarnings(False)
    GPIO.output(13,GPIO.HIGH)
    while (datetime.datetime.now().replace(microsecond=0) - startingTestTime).seconds <= testDuration:
        _thread.start_new_thread(temperatureThread, ())
        if(checkBoxAnswerRadiometer.get()==1):
            _thread.start_new_thread(radioThread, ())
        elif(checkBoxAnswerRadiometer.get()==0):
            RadioOutput="Not connected"
            
        bus_voltage = ina219.bus_voltage  # voltage on V- (load side)
        shunt_voltage = ina219.shunt_voltage  # voltage between V+ and V- across the shunt
        current = ina219.current  # current in mA
        Voltage = "{:.2f}".format(bus_voltage + shunt_voltage)
        Current = "{:.2f}".format(current)
        #Temperature=sensor1.get_temperature()
        if(checkBoxAnswerTemperature.get()==1):
            if(temperatureThreadOutput>=maximumTemperatureWarning):
                if(checkBoxAnswerFileName.get()==1):
                    workbook.close()
                GPIO.output(13,GPIO.LOW)
                GPIO.cleanup()
            messagebox.showinfo("Finish message","Over temperature")
        
        if(checkBoxAnswerFileName.get()==1):
            existingWorkingSheet = workbook.get_worksheet_by_name("Sheet1")
            existingWorkingSheet.write(treeIntervalCounter+1,0,datetime.datetime.now().strftime("%I:%M:%S") )
            existingWorkingSheet.write(treeIntervalCounter+1,1,(datetime.datetime.now() - startingTestTime).seconds)
            existingWorkingSheet.write(treeIntervalCounter+1,2,Current)
            existingWorkingSheet.write(treeIntervalCounter+1,3,Voltage)
            existingWorkingSheet.write(treeIntervalCounter+1,4,temperatureThreadOutput)
            #print(RadioOutput)
            #print(type(RadioOutput))
            #print(len(RadioOutput))
            #for chr in RadioOutput:print(chr, repr(chr))
            #result=float(RadioOutput.replace('\n','').replace('\r','').replace("'","").replace(' ',''))
            existingWorkingSheet.write(treeIntervalCounter+1,5,RadioOutput.replace('\n','').replace('\r','').replace("'","").replace(' ',''))
            #existingWorkingSheet.write(treeIntervalCounter+1,6,result*1000)
            
        
        resultTree.insert(parent='',index='end',iid=treeIntervalCounter,text="",values=(datetime.datetime.now().time().replace(microsecond=0),(datetime.datetime.now() - startingTestTime).seconds,Current,Voltage,temperatureThreadOutput,RadioOutput))
        resultTree.update()
        treeScroll.config(command=resultTree.yview)
        treeIntervalCounter=treeIntervalCounter+1
        
        time.sleep(testIntervals)
    if(checkBoxAnswerFileName.get()==1):
        workbook.close()
    GPIO.output(13,GPIO.LOW)
    GPIO.cleanup()
    messagebox.showinfo("Finish message","Test finished")
############ Main code #############
window = tk.Tk()
window.title("Monitor-GUI")
window.geometry("700x500+0+0")
window.resizable(0, 0)#fixed size frame window size


#Base frame for the entire window
frameBase = LabelFrame(window, padx=5, pady=5, width=690, height=490)
frameBase.pack_propagate(0)#fixed size frame
frameBase.pack(padx=5, pady=5)

#Top frame for the university logo
frameTop = LabelFrame(frameBase, text="Top Frame", width=670, height=130)
frameTop.grid_propagate(0)#fixed size frame
frameTop.grid(row="0",column="0")

beforeUniversityLogo=Label(frameTop, text="    ")
beforeUniversityLogo.grid(row=0,column=0)

universityLogo=Label(frameTop, text="Universidad de Jaén", fg="green" ,font="courier 30 bold")
universityLogo.grid(row=0,column=1)

#Inputs frame for the input choises
frameMiddle = LabelFrame(frameBase, text="Inputs frame", width=670, height=190)
frameMiddle.grid_propagate(0)#fixed size frame
frameMiddle.grid(row="1",column="0")

######## Inside frame 1 #########
insideFrameMiddle1 = LabelFrame(frameMiddle,width= 670)
insideFrameMiddle1.grid(row="0",column="0",sticky=W)

questionRadiometer=Label(insideFrameMiddle1, text="Do you use Radiometer?")
questionRadiometer.grid(row="0",column="0",sticky=W)

checkBoxAnswerRadiometer = IntVar()
checkBoxAnswerRadiometer.get()
Checkbutton(insideFrameMiddle1, variable=checkBoxAnswerRadiometer, command=getCheckAnswerRadiometer).grid(row="0",column="1",sticky=W)

######## Inside frame 2 ###########
insideFrameMiddle2 = LabelFrame(frameMiddle, width=670)
insideFrameMiddle2.grid(row="1",column="0",sticky=W)

testTime=Label(insideFrameMiddle2, text="How long are the test & the intervals?")
testTime.grid(row="0",column="0",sticky=W)

testTimeInput = Entry(insideFrameMiddle2,width=7)
testTimeInput.grid(row="0",column="1",sticky=W)
testTimeInput.insert(0, "test sec")

testIntervalsInput = Entry(insideFrameMiddle2,width=7)
testIntervalsInput.grid(row="0",column="2",sticky=W)
testIntervalsInput.insert(0, "int sec")

#########Inside frame 3 ##########
insideFrameMiddle3 = LabelFrame(frameMiddle, width=670)
insideFrameMiddle3.grid(row="2",column="0",sticky=W)

MaxTemperature=Label(insideFrameMiddle3, text="Do you want over temperature protection?")
MaxTemperature.grid(row="0",column="0",sticky=W)

checkBoxAnswerTemperature = IntVar()
checkBoxAnswerTemperature.get()
Checkbutton(insideFrameMiddle3, variable=checkBoxAnswerTemperature, command=getCheckAnswerOverTemperature).grid(row="0",column="1",sticky=W)

maxTemperatureInput = Entry(insideFrameMiddle3,width=15)
maxTemperatureInput.grid(row="0",column="3",sticky=W)
maxTemperatureInput.insert(0, "max temperature")
maxTemperatureInput.configure(state="disabled")


#########Inside frame 4 ##########
insideFrameMiddle4 = LabelFrame(frameMiddle, width=670)
insideFrameMiddle4.grid(row="3",column="0",sticky=W)

questionFileName=Label(insideFrameMiddle4, text="Do you want to save the data in an excel file?")
questionFileName.grid(row="0",column="0",sticky=W)

checkBoxAnswerFileName = IntVar()
checkBoxAnswerFileName.get()
Checkbutton(insideFrameMiddle4, variable=checkBoxAnswerFileName, command=getCheckAnswerFileName).grid(row="0",column="1",sticky=W)

answerFileName = Entry(insideFrameMiddle4, width=8)
answerFileName.grid(row="0",column="2")
answerFileName.insert(0, "file name")
answerFileName.configure(state="disabled")

######## Inside frame 5 ############
insideFrameMiddle6 = LabelFrame(frameMiddle, width=670)
insideFrameMiddle6.grid(row="5",column="0",sticky=W)

startButton = Button(insideFrameMiddle6,text="Start test", font="courier 12 bold", command=startButtonFunction).grid(row="4",column="1")


#Output frame for the Treeview to display the output data
frameLast = LabelFrame(frameBase, text="Output frame", width=670, height=160)
frameLast.grid_propagate(0)#fixed size frame
frameLast.grid(row="2",column="0")

treeFrame=Frame(frameLast, width=670, height=125)
treeFrame.pack_propagate(0)#fixed size frame
treeFrame.pack(pady=5)

treeScroll= Scrollbar(treeFrame)
treeScroll.pack(side=RIGHT,fill= Y)

resultTree = ttk.Treeview(treeFrame, yscrollcommand=treeScroll.set)
resultTree['columns']=("TimeC","IntervalsC_1","CurrentC_2","VoltageC_3","Temp1C_4","PowerDensityC_5")
resultTree.column("#0", width= 0, stretch=NO)
resultTree.column("TimeC" ,anchor=W,width= 70)
resultTree.column("IntervalsC_1" ,anchor=W,width= 70)
resultTree.column("CurrentC_2" ,anchor=W,width= 70)
resultTree.column("VoltageC_3" ,anchor=W,width= 70)
resultTree.column("Temp1C_4" ,anchor=W,width= 70)
resultTree.column("PowerDensityC_5" ,anchor=W,width= 90)

resultTree.heading("#0", text="",anchor=W)
resultTree.heading("TimeC", text="Time")
resultTree.heading("IntervalsC_1", text="Intervals")
resultTree.heading("CurrentC_2", text="Current")
resultTree.heading("VoltageC_3", text="Voltage")
resultTree.heading("Temp1C_4", text="Temp1")
resultTree.heading("PowerDensityC_5", text="Power Density")

resultTree.pack(padx=8)
treeScroll.config(command=resultTree.yview)#scroll adding



window.mainloop()


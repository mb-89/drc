from PyQt5 import QtCore
from PyQt5 import QtNetwork
import logging
import struct
from enum import Enum
from math import sin
import Adafruit_BBIO.ADC as ADC
import Adafruit_BBIO.PWM as PWM
import time

log = logging.getLogger("drc bbb")
AIN0 = "AIN0"

PMIN = 0.025
PMAX = 0.125
PRANGE = PMAX-PMIN

class state(Enum):
    off = 0
    startup = 1
    on = 2
    shutdown = 3
    error = -1
    notfound = -2

class DRC(QtCore.QObject):
    done = QtCore.pyqtSignal()
    def __init__(self, qtapp):
        super().__init__()
        self.qtapp = qtapp

        self.socket = QtNetwork.QUdpSocket()
        self.socket.bind(QtNetwork.QHostAddress(""), 6001)
        self.t1 = QtCore.QTimer(qtapp)
        self.t1.setInterval(10)
        self.t1.timeout.connect(self.sample)

    def start(self):
        self.socket.readyRead.connect(self.recvudp)
        self.state = state.on
        self.udpsendcnt = 0
        self.udprecvcnt = 0
        self.udpwatchdog = -1
        self.dataIn = []
        self.killcmd = False
        self.FastSamples = 0
        self.state.angle0 = 0
        self.dataIn = [0,0,0,0]
        ADC.setup()
        self.servo0 = LDX218Servo()
        self.t1.start()

    def stop(self):
        self.t1.stop()
        log.info("Stopped sending on UDP socket")
        self.done.emit()

    def recvudp(self):
        while self.socket.hasPendingDatagrams():
            data = self.socket.readDatagram(1024)
            self.dataIn = struct.unpack("{}f".format(4),data[0])
        self.udprecvcnt+=1

        self.killcmd = self.dataIn[2]>0
        self.udpwatchdog = 50

    def sample(self):
        self.time = self.FastSamples*0.01
        self.FastSamples+=1
        self.udpwatchdog -=1
        if self.udpwatchdog == 0:
            log.info("udp watchdog triggered")
            self.stop();return

        if self.killcmd and self.state == state.on:
            log.info("received kill command")
            QtCore.QTimer.singleShot(500, self.stop)
            self.state = state.shutdown
        #input
        self.angle0ref = self.dataIn[3]
        self.servo0.set(self.angle0ref)
        self.angle0act = self.servo0.sample()
        #self.angle0ref = self.servo0.ref

        

        #processing
        #output
        self.sendudp()

    def sendudp(self):
        if not self.udpsendcnt: log.debug("Started sending on UDP socket")
        dataout = [self.udpsendcnt, self.udprecvcnt, self.state.value, self.servo0.reflim, self.servo0.act]
        databytes = struct.pack("{}f".format(len(dataout)),*dataout)
        self.socket.writeDatagram(databytes, QtNetwork.QHostAddress.Broadcast, 6000)
        self.udpsendcnt+=1

class pwmchannel():
    def __init__(self, nr, freq = 20):
        per = int(1000/freq)
        if   nr == 0: self.name = "P9_14"
        elif nr == 1: self.name = "P9_16"
        elif nr == 2: self.name = "P8_13"
        else: raise UserWarning("Invalid PWM channel")
        PWM.start(self.name, 0, per)
    def set(self,set):
        PWM.set_duty_cycle(self.name, set*100)

class adcchannel():
    def __init__(self, nr, maxval = 1, minval = 0,gain=1,offset=0):
        self.name = "AIN{}".format(nr)
        self.max = maxval
        self.min = minval
        self.diff = maxval-minval
        self.gainminmax = 1/self.diff
        self.gain = gain
        self.offset = offset
    def get(self):
        r = ADC.read(self.name)
        v = (r-self.min)*self.gainminmax
        v = v*self.gain+self.offset
        #print(r,v)
        return v

class LDX218Servo(QtCore.QObject):
    def __init__(self, pwmno = 0, ainno = 0, maxspeed = 1):
        super().__init__()
        self.pwm = pwmchannel(pwmno)
        self.adc = adcchannel(ainno,0.203,0.692,-1,1)
        self.tsamp = 0.01
        self.maxspeed = maxspeed

        self.act = self.adc.get()
        self.ref = self.act
        self.reflim = self.act

    def set(self,set):
        self.ref = set
        return self.act

    def sample(self):
        self.act = self.adc.get()
        maxdiff = self.maxspeed*self.tsamp
        diff = self.ref-self.act
        if diff>maxdiff: diff = maxdiff
        if diff<-maxdiff: diff = -maxdiff
        newpos = self.act+diff
        if newpos>1:newpos = 1
        if newpos<0:newpos = 0
        s = sin(time.time())
        newpos =s*s
        d = PMIN+PRANGE*newpos
        self.reflim=newpos
        #print(self.act, newpos)
        self.pwm.set(d)
        return self.act
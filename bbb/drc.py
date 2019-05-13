from PyQt5 import QtCore
from PyQt5 import QtNetwork
import logging
import struct
from enum import Enum
from math import sin

log = logging.getLogger("drc bbb")

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
        self.t1.start()

    def stop(self):
        self.t1.stop()
        log.info("Stopped sending on UDP socket")
        self.done.emit()

    def recvudp(self):
        while self.socket.hasPendingDatagrams():
            data = self.socket.readDatagram(1024)
            self.dataIn = struct.unpack("{}f".format(3),data[0])
        self.udprecvcnt+=1

        self.killcmd = self.dataIn[2]>0
        self.udpwatchdog = 10

    def sample(self):
        self.time = self.FastSamples*0.01
        self.FastSamples+=1
        self.udpwatchdog -=1
        if self.udpwatchdog == 0: self.stop();return

        if self.killcmd and self.state == state.on:
            log.info("received kill command")
            QtCore.QTimer.singleShot(500, self.stop)
            self.state = state.shutdown
        #input
        #processing
        #output
        self.sendudp()

    def sendudp(self):
        if not self.udpsendcnt: log.debug("Started sending on UDP socket")
        s = sin(2*3.1415*self.time)
        dataout = [self.udpsendcnt, self.udprecvcnt, self.state.value, s**2]
        databytes = struct.pack("{}f".format(len(dataout)),*dataout)
        self.socket.writeDatagram(databytes, QtNetwork.QHostAddress.Broadcast, 6000)
        self.udpsendcnt+=1
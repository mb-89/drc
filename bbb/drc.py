from PyQt5 import QtCore
from PyQt5 import QtNetwork
import logging
import struct

log = logging.getLogger("drc bbb")

class DRC():
    def __init__(self, qtapp):
        self.qtapp = qtapp

        self.socket = QtNetwork.QUdpSocket()
        self.socket.bind(QtNetwork.QHostAddress(""), 6001)
        self.socket.readyRead.connect(self.recvudp)
        log.info("Connected to udp socket")
        self.sendcnt = 0
        self.recvcnt = 0

        self.t1 = QtCore.QTimer(qtapp)
        self.t1.setInterval(10)
        self.t1.timeout.connect(self.sample)
        self.t1.start()

    def recvudp(self): pass

    def sample(self):
        #input
        #processing
        #output
        self.sendudp()

    def sendudp(self):
        databytes = struct.pack("{}f".format(1),*[self.sendcnt])
        self.socket.writeDatagram(databytes, QtNetwork.QHostAddress.Broadcast, 6000)
        self.sendcnt+=1
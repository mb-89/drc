import logging
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import os.path as op
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtNetwork
import time
from enum import Enum
import struct

log = logging.getLogger("drc host")

class state(Enum):
    off = 0
    startup = 1
    on = 2
    shutdown = 3
    error = -1
    notfound = -2

class Backend(QtCore.QObject):
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    statechanged = QtCore.pyqtSignal(state)

    def __init__(self, cfg):
        super().__init__()
        self._state = state.off
        self._oldstate = state.off
        self.cfg = cfg
        self.state = state.off
        self.states = state


    def toggleStatus(self):
        if      self.state == state.off: self.start()
        elif    self.state == state.on: self.stop()

    def start(self):
        if self.state != state.off: return
        
        self.bgthread=QtCore.QThread()
        self.bgworker=BackgroundWorker(self.cfg)
        self.bgworker.moveToThread(self.bgthread)
        self.bgthread.started.connect(self.bgworker.run)
        self.bgworker.done.connect(self.bgthread.quit)
        self.bgthread.finished.connect(lambda: self._setstate(state.off))
        self.bgthread.start()
        #print(f"start / {int(QtCore.QThread.currentThreadId())}")

        self.state = state.on

    def stop(self):
        if self.state == state.off: return
        self.state = state.shutdown
        self.bgworker.shutdown()

    def _setstate(self, x): self.state = x
    @property
    def state(self): return self._state
    @state.setter
    def state(self, x):
        self._state = x
        self.statechanged.emit(x)
        if self._state == state.on:
            self.started.emit()
            log.info("Connected to bbb", extra = log.HST)
        if self._state == state.off:
            if self._oldstate != state.shutdown and self._oldstate != state.off:
                log.error("Connection to bbb interrupted", extra = log.HST)
            else:
                log.info("Disconnected from bbb", extra = log.HST)
            self.stopped.emit()
        self._oldstate = self._state

class BackgroundWorker(QtCore.QObject):
    done = QtCore.pyqtSignal()
    def __init__(self,cfg):
        super().__init__()
        self.cfg = cfg
        #print(f"{int(QtCore.QThread.currentThreadId())}")
    def run(self):
        self.remotestartup()
        self.updstartup()
        self.SlowSamples = 0
        self.FastSamples = 0
        self.killcmd = False
        self.t1 = QtCore.QTimer()
        self.t1.setInterval(100)
        self.t1.timeout.connect(self.sampleSlow)
        self.t1.start()
        self.t2 = QtCore.QTimer()
        self.t2.setInterval(10)
        self.t2.timeout.connect(self.sampleFast)
        self.t2.start()

    def sampleSlow(self):
        #print(f"{self.samples} / {int(QtCore.QThread.currentThreadId())}")
        self.SlowSamples+=1
        self.remoteIsRunning = not self.sshout.channel.exit_status_ready()
        if self.remoteIsRunning and self.sshout.channel.recv_ready():
            input = [x.strip() for x in self.sshout.channel.recv(1024).decode("utf-8").split("\n")]
            input = [x for x in input if x]
            for x in input: log.debug(x, extra = log.BBB)
        if not self.remoteIsRunning:
            input = [x.strip() for x in self.sshout.channel.recv(1024).decode("utf-8").split("\n")]
            input = [x for x in input if x]
            for x in input: log.debug(x, extra = log.BBB)
            self.disconnect()

    def sampleFast(self):
        self.FastSamples+=1
        disc = (self.udprecvcnt-self.udprecvcntold)>5 and self.udprecvcnt>0
        disc |= (self.udprecvcnt-self.udprecvcntold)>100
        if disc:
            self.disconnect();return
        self.udprecvcntold = self.udprecvcnt
        self.sendudp()

    def disconnect(self):
        self.done.emit()

    def updstartup(self):
        self.udprecvcnt = 0
        self.udprecvcntold = 0
        self.udpsendcnt = 0
        self.socket = QtNetwork.QUdpSocket()
        self.socket.bind(QtNetwork.QHostAddress(""), 6000)
        self.socket.readyRead.connect(self.recvudp)
        log.debug("Connected to socket, waiting for udp stream", extra = log.HST)

    def recvudp(self):
        if self.udprecvcnt == 0:
            log.debug("udp stream received", extra = log.HST)
        while self.socket.hasPendingDatagrams():
            data = self.socket.readDatagram(1024)
            self.dataIn = struct.unpack("{}f".format(3),data[0])
            #if self.udprecvcnt%100==0:log.debug(self.dataIn, extra = log.HST)
        self.udprecvcnt+=1

    def sendudp(self):
        databytes = struct.pack("{}f".format(3),*[self.udpsendcnt, self.udprecvcnt, self.killcmd])
        self.socket.writeDatagram(databytes, QtNetwork.QHostAddress.Broadcast, 6001)
        self.udpsendcnt+=1

    def shutdown(self):
        self.killcmd=True
    def remotestartup(self):
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy)
        ssh.connect(
            self.cfg["connection"]["bbbip"],
            username=self.cfg["connection"]["bbbuser"], 
            password=self.cfg["connection"]["bbbpw"])

        #create the destination folder if it does not exist
        log.debug("updating bbb program", extra = log.HST)
        src = op.abspath(self.cfg["connection"]["bbbsrc"])
        dst = self.cfg["connection"]["bbbdst"]
        (sshin1, sshout1, ssherr1) = ssh.exec_command(f"mkdir -p {dst}")

        #copy the cfg file and the bbb code
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(self.cfg.filename, remote_path=dst)
            scp.put(src, recursive=True, remote_path=dst)
        (sshin2, sshout2, ssherr2) = ssh.exec_command(f"python3 {dst}/bbb/__main__.py",get_pty=True)
        log.debug("started bbb program", extra = log.HST)
        self.sshout = sshout2
        self.ssh = ssh
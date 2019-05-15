import logging
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import os.path as op
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtNetwork
import time
from enum import Enum
import struct
from subprocess import Popen,STDOUT
from collections import deque

log = logging.getLogger("drc host")
FNULL = open(os.devnull, 'w')

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
        self.state = state.notfound
        self.states = state
        self.slowtimer = QtCore.QTimer()
        self.slowtimer.setInterval(1000)
        self.slowtimer.timeout.connect(self.slowSample)
        self.pingprocess = None
        self.slowtimer.start()
        self.data = deque(maxlen=30*100)
        self.cacheusage = 0
        self.slowSample()

    def slowSample(self):
        self.ping()
        self.cleardatacache()

    def cleardatacache(self):
        clear = len(self.data)>30*100*0.9
        while clear and len(self.data)>30*100*0.5:
            self.data.popleft()

    def ping(self):
        if self.state == state.off or self.state == state.notfound:
            if self.pingprocess is None:
                self.pingprocess = Popen(
                    ['ping','-n','1',"-w", "10", self.cfg["connection"]["bbbip"]],
                    stdout=FNULL, stderr=STDOUT)
            else:
                self.pingprocess.communicate(input='\n')
                ret = self.pingprocess.returncode
                if ret is not None:
                    if ret == 0 and self.state != state.off: self.state = state.off
                    elif ret != 0 and self.state != state.notfound: self.state = state.notfound
                    self.pingprocess = None

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
        self.bgworker.dataRecv.connect(self.storeData)
        self.bgthread.finished.connect(lambda: self._setstate(state.off))
        self.bgthread.start()
        #print(f"start / {int(QtCore.QThread.currentThreadId())}")

        self.state = state.on

    def stop(self):
        if self.state == state.off: return
        self.state = state.shutdown
        self.bgworker.shutdown()

    def storeData(self, newrow):
        self.data.append((time.time(), *newrow))

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
            if self._oldstate != state.notfound and self._oldstate != state.shutdown and self._oldstate != state.off:
                log.error("Connection to bbb interrupted", extra = log.HST)
            elif self._oldstate != state.notfound:
                log.info("Disconnected from bbb", extra = log.HST)
            self.stopped.emit()
        self._oldstate = self._state

class BackgroundWorker(QtCore.QObject):
    done = QtCore.pyqtSignal()
    dataRecv = QtCore.pyqtSignal(tuple)
    def __init__(self,cfg):
        super().__init__()
        self.cfg = cfg
        print(f"{int(QtCore.QThread.currentThreadId())}")
    def run(self):
        self.remotestartup()
        self.updstartup()
        self.udpwatchdog = -1
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
        self.angle0set = 0

    def sampleSlow(self):
        #print(f"{self.samples} / {int(QtCore.QThread.currentThreadId())}")
        self.SlowSamples+=1
        self.remoteIsRunning = not self.sshout.channel.exit_status_ready()
        if self.sshout.channel.recv_ready():
            input = [x.strip() for x in self.sshout.channel.recv(1024).decode("utf-8").split("\n")]
            input = [x for x in input if x]
            for x in input: log.debug(x, extra = log.BBB)
        if not self.remoteIsRunning: self.disconnect()

    def sampleFast(self):
        self.FastSamples+=1
        self.udpwatchdog -=1
        if self.udpwatchdog == 0: self.disconnect();return

        self.sendudp()

    def disconnect(self):
        self.socket.close()
        self.done.emit()

    def updstartup(self):
        self.udprecvcnt = 0
        self.udpsendcnt = 0
        self.socket = QtNetwork.QUdpSocket()
        self.socket.bind(QtNetwork.QHostAddress(""), 6000)
        self.socket.readyRead.connect(self.recvudp)
        log.debug("Connected to socket, waiting for udp stream", extra = log.HST)

    def recvudp(self):
        while self.socket.hasPendingDatagrams():
            data = self.socket.readDatagram(1024)
            self.dataIn = struct.unpack("{}f".format(5),data[0])
            self.dataRecv.emit(self.dataIn)
            if self.udprecvcnt%100==0:log.debug(self.dataIn, extra = log.HST)
        self.udprecvcnt+=1
        self.udpwatchdog = 10

    def sendudp(self):
        if self.udprecvcnt < 1: return
        data = [self.udpsendcnt, self.udprecvcnt, self.killcmd, self.angle0set]
        databytes = struct.pack("{}f".format(len(data)),*data)
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
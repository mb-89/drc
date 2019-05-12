import logging
from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient
import os.path as op
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtNetwork
import time
from enum import Enum

log = logging.getLogger("drc host")

class state(Enum):
    off = 0
    startup = 1
    on = 2
    shutdown = 3
    error = -1

class Backend(QtCore.QObject):
    started = QtCore.pyqtSignal()
    stopped = QtCore.pyqtSignal()
    statechanged = QtCore.pyqtSignal(state)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.state = state.off
        self.states = state

    def toggleStatus(self):
        if      self.state == state.off: self.start()
        elif    self.state == state.on: self.stop()

    def start(self):
        if self.state != state.off: return

        #first create the bg worker, ...
        self.bgthread = QtCore.QThread()
        self.bgworker = Backgroundworker(self.cfg)
        #then move it to thread, ...
        self.stopped.connect(self.bgworker.stop)
        self.bgworker.moveToThread(self.bgthread)
        self.bgthread.started.connect(self.bgworker.run)
        self.bgworker.finished.connect(self.bgthread.quit)

        #then connect signals and slots
        self.started.connect(self.bgthread.start)
        self.bgworker.statechanged.connect(self._setstate)
        
        self.started.emit()
        QtCore.QTimer.singleShot(7000, lambda: self.stopped.emit)

    def stop(self):
        if self.state == state.off: return
        self.stopped.emit()

    def _setstate(self, x): self.state = x
    @property
    def state(self): return self._state
    @state.setter
    def state(self, x):
        self._state = x
        self.statechanged.emit(x)

class Backgroundworker(QtCore.QObject):
    statechanged = QtCore.pyqtSignal(state)
    finished = QtCore.pyqtSignal()
    def __init__(self, cfg): #this init is called before we are moved to annother thread
        super().__init__()
        self.cfg = cfg

    @QtCore.pyqtSlot()      #this init is called when we are in the correct thread
    def run(self):
        self.state = state.off
        self.remotestartup()
        self.setupUDPsocket()
        self.state = state.on
        while self.state != state.shutdown:
            time.sleep(0.1)
            self.pollsshlogger()
        self.quit()

    def stop(self):
        self.state = state.shutdown

    def quit(self):
        self.state = state.off
        self.finished.emit()

    @property
    def state(self): return self._state

    @state.setter
    def state(self, x):
        self._state = x
        self.statechanged.emit(x)

    @QtCore.pyqtSlot()
    def remotestartup(self):
        if self.state != state.off: return
        self.state = state.startup
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy)
        ssh.connect(
            self.cfg["connection"]["bbbip"],
            username=self.cfg["connection"]["bbbuser"], 
            password=self.cfg["connection"]["bbbpw"])

        #create the destination folder if it does not exist
        log.info("updating bbb program", extra = log.HST)
        src = op.abspath(self.cfg["connection"]["bbbsrc"])
        dst = self.cfg["connection"]["bbbdst"]
        (sshin1, sshout1, ssherr1) = ssh.exec_command(f"mkdir -p {dst}")

        #copy the cfg file and the bbb code
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(self.cfg.filename, remote_path=dst)
            scp.put(src, recursive=True, remote_path=dst)
        (sshin2, sshout2, ssherr2) = ssh.exec_command(f"python3 {dst}/bbb/__main__.py",get_pty=True)
        log.info("started bbb program, waiting for udp stream", extra = log.HST)
        self.sshout = sshout2
        self.ssh = ssh
        self.sshtimer = QtCore.QTimer(self)
        self.sshtimer.setInterval(100)
        self.sshtimer.timeout.connect(self.pollsshlogger)
        #self.sshtimer.start()
        #self.pollsshlogger()

    @QtCore.pyqtSlot()
    def pollsshlogger(self):
        log.info("poll", extra = log.HST)
        running = not self.sshout.channel.exit_status_ready()
        if running:
            rawinput = self.sshout.channel.recv(1024).decode("utf-8").strip()
            for x in rawinput.split("\n"):
                    if x:log.info(x, extra = log.BBB)

    def setupUDPsocket(self):
        self.recvcnt = 0
        self.sendcnt = 0
        self.socket = QtNetwork.QUdpSocket()
        self.socket.bind(QtNetwork.QHostAddress(""), 6000)
        self.socket.readyRead.connect(self.recvudp)
        log.info("Connected to udp socket", extra = log.HST)

    def recvudp(self):
        if not self.recvcnt:
            log.info("udp stream received", extra = log.HST)
        self.recvcnt+=1
        
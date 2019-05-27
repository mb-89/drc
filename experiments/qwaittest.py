import logging
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import QtTest
from PyQt5 import uic
import os.path as op
from functools import partial
from time import time

import logging
log = logging.getLogger("updatingmodel")
log.DEBUG = logging.DEBUG
log.INFO = logging.INFO
log._fmt = logging.Formatter('%(relativeCreated)09d | %(levelname)s | %(message)s')
logHandler = logging.StreamHandler()
logHandler.setFormatter(log._fmt)
log.addHandler(logHandler)
log.setLevel(log.DEBUG)
logHandler.setLevel(log.DEBUG)

class Frontend():
    def __init__(self, app):
        self.qtapp = app
        self.window = QtWidgets.QMainWindow()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.sample)
        self.timer.start()
        self.wait = QtTest.QTest.qWait
        self.nr = 0

    def sample(self):
        nr = self.nr+1
        self.nr+=1
        log.info(f"before wait {nr}")
        self.wait(1000)
        log.info(f"after wait {nr}")

    def run(self):
        self.window.show()
        sys.exit(self.qtapp.exec_())

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    fe = Frontend(app)
    fe.run()
import os.path as op
from PyQt5 import QtWidgets
import sys

from host import logger
from host import cfg
from host import frontend
from host import backend

qtapp = QtWidgets.QApplication(sys.argv)
qtapp.setStyle("Fusion")
be = backend.Backend(cfg.Cfg("cfg/params"))
fe = frontend.Frontend(be,qtapp)

fe.run()
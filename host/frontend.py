import logging
import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
import os.path as op
from functools import partial
from host.plotter import plotter

log = logging.getLogger("drc host")

class Frontend():
    def __init__(self, backend,qtapp):
        self.qtapp = qtapp
        self.backend = backend
        self.window = MainWindow(self.qtapp, self, backend)

    def run(self):
        self.window.run()
    
    def statechanged(self, newstate):
        print(newstate)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, qtapp,frontend,backend):
        super().__init__()
        self.qtapp = qtapp
        self.frontend = frontend
        self.backend = backend
        self.plotter = None
        self.ui = uic.loadUi(op.dirname(__file__)+"/frontend.ui", self)
        self.ui.statusBar.setSizeGripEnabled(False)
        self.setup()

    def setup(self):
        self.backend.statechanged.connect(self.updateStatus)
        self.setupLogging()
        self.setupstatusindicator()
        self.ui.actionToggle_State.triggered.connect(self.statusButton.click)
        self.ui.actionPlotter.triggered.connect(self.showPlotter)

    def run(self):
        self.show()
        sys.exit(self.qtapp.exec_())

    def setupstatusindicator(self):
        self.statusIndicator = QtWidgets.QRadioButton()
        self.statusButton = QtWidgets.QPushButton()
        self.statusIndicator.setCheckable(False)
        self.statusButton.setMaximumHeight(14)
        self.statusButton.setMaximumWidth(40)
        ss = self.statusButton.styleSheet()
        self.statusButton.setStyleSheet("text-align:center;vertical-align:middle")
        self.statusButton.clicked.connect(self.backend.toggleStatus)

        self.indicators = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        self.indicators.setLayout(layout)
        layout.addWidget(self.statusIndicator)
        layout.addWidget(self.statusButton)

        self.ui.statusBar.addPermanentWidget(self.indicators)
        self.updateStatus(0)

    def updateStatus(self, backendstate):
        if backendstate == self.backend.states.on:
            self.statusIndicator.setStyleSheet(
                "QRadioButton::indicator{border: 1px solid darkgray;background-color: rgb(177, 231, 185);border-radius: 8px;}")
            self.statusButton.setText("DIS")
        elif (backendstate == self.backend.states.startup) or (backendstate == self.backend.states.shutdown):
            self.statusIndicator.setStyleSheet(
                "QRadioButton::indicator{border: 1px solid darkgray;background-color: rgb(248, 229, 123);border-radius: 8px;}")
            self.statusButton.setText("---")
        elif backendstate == self.backend.states.error:
            self.statusIndicator.setStyleSheet(
                "QRadioButton::indicator{border: 1px solid darkgray;background-color: rgb(248, 123, 123);border-radius: 8px;}")
            self.statusButton.setText("RST")
        elif backendstate == self.backend.states.off:
            self.statusIndicator.setStyleSheet(
                "QRadioButton::indicator{border: 1px solid darkgray;background-color: light gray;border-radius: 8px;}")
            self.statusButton.setText("CON")
        else:
            self.statusIndicator.setStyleSheet(
                "QRadioButton::indicator{border: 1px solid darkgray;background-color: light gray;border-radius: 8px;}")
            self.statusButton.setText("---")

    def setupLogging(self):
        #create a text widget & status bar to log into
        self.logging = QtWidgets.QTextEdit()
        self.logging.setReadOnly(True)
        self.logging.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.logging.customContextMenuRequested.connect(
            lambda x:self.LogContextMenu(self.logging, x))
        QtHandler = QtLog2TextEditHandler()
        QtHandler.setFormatter(log._fmt)
        QtHandler.sig.connect(self.logging.append)
        QtHandler.sig.connect(lambda x: self.statusBar.showMessage(x,0))
        log.addHandler(QtHandler)
        log.info("started logging to GUI", extra = log.HST)

        #make the text widget dockable
        self.loggingDock = QtWidgets.QDockWidget(self)
        self.loggingDock.hide()
        self.loggingDock.setWidget(self.logging)
        self.loggingDock.setFloating(True)
        self.loggingDock.resize(800,200)
        self.loggingDock.setWindowTitle(f"drc log")
        self.ui.actionLog.triggered.connect(
            lambda: self.loggingDock.setVisible(self.loggingDock.isHidden()))

    def showPlotter(self):
        if self.plotter is None:
            self.plotter = plotter.Plotter(self.backend.data)
            self.plotter.show()

class QtLog2TextEditHandler(QtCore.QObject,logging.StreamHandler):
    sig = QtCore.pyqtSignal(str)
    def __init__(self):
        super().__init__()

    def emit(self, logRecord):
        msg = self.format(logRecord)
        self.sig.emit(msg)
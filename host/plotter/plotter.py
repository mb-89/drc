import pyqtgraph as pg
#pg.setConfigOptions(antialias=True)
pg.setConfigOptions(useOpenGL=True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from time import time
from math import sin
import itertools
import copy
import threading

class Plotter(QtCore.QObject):
    def __init__(self,datasrc):
        super().__init__()
        self.datarsrc = datasrc
    def show(self):
        self.window = PlotterWindow(self.datarsrc)
        self.window.show()

class PlotterWindow(pg.GraphicsWindow):
    def __init__(self,datasrc):
        super().__init__()
        self.datasrc = datasrc
        self.chunksize = 100
        self.setWindowTitle("realtime plot")
        self.p = self.addPlot()
        self.v = self.p.getViewBox()
        self.line0 = self.p.plot(pen=pg.mkPen((0,2),color='r'))
        self.line1 = self.p.plot(pen=pg.mkPen((1,2),color='r'))
        self.p.setLabel('bottom','Time','s')
        self.p.setXRange(0,1000)
        self.line0.setData(x=[x for x in range(1000)])
        self.line1.setData(x=[x for x in range(1000)])
        self.data = np.empty(( self.chunksize+1,2))
        self.splines = []
        self.currSample = 0
        self.t0 = time()
        self.tmax = 10
        self.lasttime = self.t0

        self.timer = QtCore.QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def update(self):
        maxidx = int(min(len(self.datasrc), 1000))
        #with threading.Lock():
        tmp = [self.datasrc[-idx-1] for idx in range(maxidx)]
        if maxidx==0:
            self.t0 = time()
            self.tmax = 10
            return
        t1 = tmp[0][0]-self.t0

        self.line0.setData(y=[x[-2] for x in tmp])
        self.line1.setData(y=[x[-1] for x in tmp])
        if t1 <= self.tmax: return
        #self.v.translateBy(x=t1-self.tmax)
        self.tmax = t1


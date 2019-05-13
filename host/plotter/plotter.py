import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
from time import time
from math import sin

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
        self.p.setLabel('bottom','Time','s')
        self.p.setXRange(-10,0)
        self.data = np.empty(( self.chunksize+1,2))
        self.splines = []
        self.currSample = 0
        self.t0 = time()
        self.lasttime = self.t0

        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def update(self):
        Idx = -1
        while True:
            try: sample = self.datasrc[Idx]
            except IndexError: break
            t = sample[0]
            v = sample[-1]
            self.addsample(t-self.t0,v)
            if t<=self.lasttime:break
            Idx-=1
        self.lasttime=time()

    def addsample(self,t,y):
        for s in self.splines: s.setPos(-t,0)
        idx = self.currSample % self.chunksize
        if idx == 0:
            newspline = self.p.plot()
            self.splines.append(newspline)
            lastdata = self.data[-1]
            self.data = np.empty(( self.chunksize+1,2))
            self.data[0] = lastdata
            while len(self.splines)>21:
                s = self.splines.pop(0)
                self.p.removeItem(s)
        else:
            newspline = self.splines[-1]
        self.data[idx+1,0] = t
        self.data[idx+1,1] =  y
        newspline.setData(x=self.data[:idx+2,0], y=self.data[:idx+2,1])
        self.currSample +=1

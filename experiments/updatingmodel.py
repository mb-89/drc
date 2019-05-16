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
        self.window = MainWindow(app)

    def run(self):
        self.window.run()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self,app):
        super().__init__()
        self.qtapp = app
        self.ui = uic.loadUi(op.abspath(op.dirname(__file__))+"/updatingmodel.ui", self)
        self.setup()

    def setup(self):
        self.src = modelDataSrc()
        self.model = UpdatingModel(self.src)
        self.model.setColumnCount(2)
        self.ui.treeView.setModel(self.model)
        self.ui.treeView.expanded.connect(self.model.discover)
        self.updateTimer = QtCore.QTimer()
        self.updateTimer.setInterval(2000)
        self.updateTimer.timeout.connect(lambda:self.model.data.c1.c1.c1._set(time()))
        self.updateTimer.start()

    def run(self):
        self.show()
        sys.exit(self.qtapp.exec_())

class UpdatingModel(QtGui.QStandardItemModel):
    def __init__(self, datasrc):
        super().__init__()
        self.items = []
        self.datasrc = datasrc
        ROOT = UpdatingItem("ROOT")
        self.invisibleRootItem().appendRow([ROOT])
        self.data = ROOT.item
        self.data._getChildren()
    def discover(self, index):
        item = self.itemFromIndex(index)
        for chidx in range(item.rowCount()):
            item.child(chidx).discover()

class UpdatingItem(QtGui.QStandardItem):
    def __init__(self, name):
        super().__init__(name)
        self.item = DirectAccessItem(self)
    def discover(self):
        if not self.item._discovered:
            self.item._getChildren()

class DirectAccessItem():
    def __init__(self, qtItem):
        self._qtItem = qtItem
        self._qtValue = QtGui.QStandardItem("")
        self._name = qtItem.text()
        self._discovered = False
        self._visible = True
        self._value = None
    def _parent(self): 
        qtp = self._qtItem.parent()
        if qtp: return qtp.item
        return None
    def _getChildren(self, _childList = None):
        if _childList is None:
            self._qtItem.model().datasrc.getChildren(self._fullpath, self._getChildren)
        else:
            for chname in _childList:
                qtItem = UpdatingItem(chname)
                self._qtItem.appendRow([qtItem, qtItem.item._qtValue])
                setattr(self,chname,qtItem.item)
            self.discovered = True
    def _set(self, val):
        self._value = val
        self._qtValue.setText(f"{val}")
    def __getattr__(self, name):
        #only called if attr not found
        if not self._discovered:
            log.info("didnt find {name} in {self.fullpath}")
            self._qtItem.model().datasrc.getChildren(self._fullpath, self._getChildren)
            for cnt in range(3):
                QtTest.QTest.qWait(750)
                if self._discovered:
                    break
            return self.__getattribute__(name)
        return None

    def _fullpath(self,join=None):
        p = [self.name]
        target = self._parent()
        while target:
            p.append(target.name)
            target=target.parent()
        p.reverse()
        if join is not None: return join.join(p)
        return p
        
class modelDataSrc():
    def __init__(self):
        pass
    def getChildren(self, path, callback):
        QtCore.QTimer.singleShot(500,lambda:callback(["c1","c2","c3"]))


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    fe = Frontend(app)
    fe.run()
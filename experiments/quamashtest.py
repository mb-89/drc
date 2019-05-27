import asyncio
import atexit

from quamash import QEventLoop
from PyQt5 import QtGui, QtCore, QtWidgets
from pyqtgraph import dockarea # Will import PyQt5.QtGui.QApplication


class MainWindow(QtGui.QMainWindow):
    def __init__(self, app, server):
        super().__init__()
        self.exit_request = asyncio.Event()
        self.treeview = QtWidgets.QTreeView()
        self.treeview.setMinimumSize(400,400)
        self.setCentralWidget(self.treeview)
        self.src = modelDataSrc()
        self.model = UpdatingModel(self.src)
        self.model.setColumnCount(2)
        self.treeview.setModel(self.model)
        self.treeview.expanded.connect(lambda x: asyncio.ensure_future(self.model.discover(x)))

    def closeEvent(self, *args):
        self.exit_request.set()

    def save_state(self):
        return bytes(self.saveGeometry())

    def restore_state(self, state):
        self.restoreGeometry(QtCore.QByteArray(state))


async def slow_operation(n):
    await asyncio.sleep(0.1)
    print("Slow operation {} complete".format(n))

class modelDataSrc():
    def __init__(self):
        pass
    async def getChildren(self, path):
        await asyncio.sleep(0.1)
        return ["c1","c2","c3"]

class UpdatingModel(QtGui.QStandardItemModel):
    def __init__(self, datasrc):
        super().__init__()
        self.items = []
        self.datasrc = datasrc
        ROOT = UpdatingItem("ROOT")
        self.invisibleRootItem().appendRow([ROOT])
        self.data = ROOT.item
        asyncio.ensure_future(self.data._getChildren())

    async def discover(self, index):
        item = self.itemFromIndex(index)
        for chidx in range(item.rowCount()):
            await item.child(chidx).discover()

class UpdatingItem(QtGui.QStandardItem):
    def __init__(self, name):
        super().__init__(name)
        self.item = DirectAccessItem(self)
    async def discover(self):
        if not self.item._discovered:
            await self.item._getChildren()

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
    async def _getChildren(self):
        children = await self._qtItem.model().datasrc.getChildren(self._fullpath)
        for chname in children:
            qtItem = UpdatingItem(chname)
            self._qtItem.appendRow([qtItem, qtItem.item._qtValue])
            setattr(self,chname,qtItem.item)
        self.discovered = True

    def _fullpath(self,join=None):
        p = [self.name]
        target = self._parent()
        while target:
            p.append(target.name)
            target=target.parent()
        p.reverse()
        if join is not None: return join.join(p)
        return p

async def main():
    await asyncio.wait([
        slow_operation(1),
        slow_operation(2),
        slow_operation(3),
    ])


app = QtGui.QApplication([])
loop = QEventLoop(app)
asyncio.set_event_loop(loop)
atexit.register(loop.close)
#loop = asyncio.get_event_loop()
win = MainWindow(app, None)

win.show()
loop.run_until_complete(win.exit_request.wait())
loop.run_until_complete(main())
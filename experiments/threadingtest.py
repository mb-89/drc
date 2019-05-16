from PyQt5 import QtCore, QtGui, QtWidgets
import time
import sys
def main():
    app = QtWidgets.QApplication(sys.argv)
    t=QtCore.QThread()
    w=Worker()
    w.moveToThread(t)
    t.started.connect(w.run)
    w.done.connect(t.quit)
    t.finished.connect(app.quit)
    t.start()
    print(f"start / {int(QtCore.QThread.currentThreadId())}")
    sys.exit(app.exec_())

class Worker(QtCore.QObject):
    done = QtCore.pyqtSignal()
    def __init__(self):
        super().__init__()
        print(f"{int(QtCore.QThread.currentThreadId())}")
    def run(self):
        self.samples = 0
        self.t1 = QtCore.QTimer()
        self.t1.setInterval(100)
        self.t1.timeout.connect(self.sample)
        self.t1.start()
    def sample(self):
        print(f"{self.samples} / {int(QtCore.QThread.currentThreadId())}")
        self.samples+=1
        if self.samples>20:self.done.emit()



if __name__ == "__main__": main()
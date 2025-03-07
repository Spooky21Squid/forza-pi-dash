from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread

import socket
import time
from fdp import ForzaDataPacket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)
sock.bind(('', 1337))

class Worker(QObject):
    finished = Signal()
    collected = Signal(bytes)

    @Slot()
    def __init__(self):
        super(Worker, self).__init__()
        self.working = True

    def work(self):
        while self.working:
            try:
                data, address = sock.recvfrom(1024)
                print('received {} bytes from {}'.format(len(data), address))
                #time.sleep(0.05)
                self.collected.emit(data)
            except BlockingIOError:
                #print("Not available, trying again...")
                #time.sleep(1)
                pass
                

        self.finished.emit()


class GearIndicator(QtWidgets.QLCDNumber):
    def __init__(self):
        super().__init__()
        self.initWidget()
    
    def initWidget(self):
        self.display(0)


class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

        self.initWidget()

    
    def initWidget(self):
        self.resize(800, 480)

        self.listenButton = QtWidgets.QPushButton()
        self.listenButton.setCheckable(True)  # make toggleable
        self.listenButton.clicked.connect(self.toggle_loop)

        self.gearIndicator = GearIndicator()

        self.slider = QtWidgets.QSlider(Qt.Horizontal)
        self.slider.setMaximum(7)
        self.slider.setMinimum(0)
        self.slider.valueChanged.connect(self.gearIndicator.display)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.gearIndicator)
        layout.addWidget(self.slider)
        layout.addWidget(self.listenButton)
        self.setLayout(layout)
    
    def loop_finished(self):
        print("Finished listening")
    
    def onCollected(self, data):
        print("Received Data")
        fdp = ForzaDataPacket(data)
        if fdp.is_race_on:
            self.gearIndicator.display(fdp.gear)

    
    @Slot()
    def toggle_loop(self, checked):
        if not checked:
            self.worker.working = False
            print("worker set to false")
            self.thread.quit()
        else:
            print("thread is started")
            self.worker = Worker()  # a new worker to perform those tasks
            self.thread = QThread()  # a new thread to run our background tasks in
            self.worker.moveToThread(self.thread)
            # move the worker into the thread, do this first before connecting the signals
            self.thread.started.connect(self.worker.work)
            # begin our worker object's loop when the thread starts running
            self.worker.collected.connect(self.onCollected)
            self.worker.finished.connect(self.loop_finished)  # do something in the gui when the worker loop ends
            #self.pushButton_2.clicked.connect(self.stop_loop)  # stop the loop on the stop button click

            self.worker.finished.connect(self.thread.quit)  # tell the thread it's time to stop running
            self.worker.finished.connect(self.worker.deleteLater)  # have worker mark itself for deletion
            self.thread.finished.connect(self.thread.deleteLater)  # have thread mark itself for deletion
            # make sure those last two are connected to themselves or you will get random crashes
            self.thread.start()
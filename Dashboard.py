from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from ParamWidgets import TireSlipWidget

import socket
import time
from fdp import ForzaDataPacket
import select

from enum import Enum

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)  # Set to non blocking, so thread can be terminated without socket blocking forever
sock.bind(('', 1337))
timeout = 2

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
                ready = select.select([sock], [], [], timeout)
                if ready[0]:
                    data, address = sock.recvfrom(1024)
                    print('received {} bytes from {}'.format(len(data), address))
                    self.collected.emit(data)
                #data, address = sock.recvfrom(1024)
                #print('received {} bytes from {}'.format(len(data), address))
                #time.sleep(0.05)
                #self.collected.emit(data)
            except BlockingIOError:
                print("Not available, trying again...")
                #time.sleep(1)
                pass
                

        self.finished.emit()


class GearIndicator(QtWidgets.QLCDNumber):
    def __init__(self):
        super().__init__()
        self.initWidget()
    
    def initWidget(self):
        self.setDigitCount(1)
        self.display(0)
    
    class GearChange(Enum):
        STAY = 1
        READY = 2
        CHANGE = 3
    
    def changeState(self, state: GearChange):
        if state == self.GearChange.CHANGE:
            self.setProperty("change", True)
            self.setProperty("stay", False)
            self.setProperty("ready", False)
        
        if state == self.GearChange.READY:
            self.setProperty("change", False)
            self.setProperty("stay", False)
            self.setProperty("ready", True)
        
        if state == self.GearChange.STAY:
            self.setProperty("change", False)
            self.setProperty("stay", True)
            self.setProperty("ready", False)
        
        self.style().polish(self)


"""A compund widget that simply Displays the name of a parameter, and the value of
that parameter below it. Eg. tire_temp_FL display the tempatarure
of the front left tire. They can be simply organised vertically
or horizontally, like blocks.

paramName: The configuration name of the parameter
paramLabel: The user-friendly label for the widget
paramValue: The value the parameter currently holds"""
class ParamWidget(QtWidgets.QFrame):
    def __init__(self, paramName: str, paramLabel: str, paramValue = "0"):
        super().__init__()

        self.paramName = paramName
        self.paramLabel = QtWidgets.QLabel(paramLabel)
        self.paramValue = QtWidgets.QLabel(paramValue)

        self.initWidget()

    def initWidget(self):
        self.paramLabel.setAlignment(Qt.AlignCenter)
        self.paramValue.setAlignment(Qt.AlignCenter)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.paramLabel)
        layout.addWidget(self.paramValue)
        self.setLayout(layout)


class Dashboard(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None
        self.paramDict = {}

        # A dict of DisplayWidgets, used to quickly update each widget with the latest value
        self.paramDict = {}

        self.initWidget()

    
    def initWidget(self):
        self.resize(800, 480)

        self.listenButton = QtWidgets.QPushButton()
        self.slipRL = TireSlipWidget()
        self.slipRR = TireSlipWidget()
        self.gearIndicator = GearIndicator()
        self.groupWidget = QtWidgets.QWidget()
        self.centreWidget = QtWidgets.QFrame()

        self.slip = ParamWidget("tire_slip_ratio_RL", "RL Slip")
        self.fuel = ParamWidget("fuel", "Fuel")
        self.distance = ParamWidget("dist_traveled", "Distance")
        self.speed = ParamWidget("speed", "Speed")

        self.listenButton.setCheckable(True)  # make toggleable
        self.listenButton.clicked.connect(self.toggle_loop)

        self.gearIndicator.setObjectName("gearIndicator")

        self.paramDict["race_pos"] = self.slip
        self.paramDict["fuel"] = self.fuel
        self.paramDict["Distance"] = self.distance
        self.paramDict["speed"] = self.speed
        
        groupLayout = QtWidgets.QHBoxLayout()
        groupLayout.addWidget(self.slip)
        groupLayout.addWidget(self.fuel)
        groupLayout.addWidget(self.distance)
        groupLayout.addWidget(self.speed)
        groupLayout.setSpacing(0)
        groupLayout.setContentsMargins(0,0,0,0)
        self.groupWidget.setLayout(groupLayout)

        centreLayout = QtWidgets.QVBoxLayout(self)
        centreLayout.addWidget(self.gearIndicator)
        centreLayout.addWidget(self.groupWidget)
        centreLayout.addWidget(self.slipRL)
        centreLayout.addWidget(self.listenButton)
        centreLayout.setSpacing(0)
        centreLayout.setContentsMargins(0,0,0,0)
        self.centreWidget.setLayout(centreLayout)

        mainLayout = QtWidgets.QHBoxLayout(self)
        mainLayout.addWidget(self.slipRL)
        mainLayout.addWidget(self.centreWidget)
        mainLayout.addWidget(self.slipRR)
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0,0,0,0)
        self.setLayout(mainLayout)

        # Just to test
        self.slipRL.setValue(50)
    
    def loop_finished(self):
        print("Finished listening")

        ## Reset the tire slip indicator bars
        self.slipRR.reset()
        self.slipRL.reset()
    
    def updateParamWidgets():
        pass
    
    def onCollected(self, data):
        print("Received Data")
        fdp = ForzaDataPacket(data)
        if fdp.is_race_on:
            self.gearIndicator.display(fdp.gear)

            if fdp.current_engine_rpm / fdp.engine_max_rpm >= 0.8:
                self.gearIndicator.changeState(GearIndicator.GearChange.CHANGE)
            elif fdp.current_engine_rpm / fdp.engine_max_rpm >= 0.75 and fdp.current_engine_rpm / fdp.engine_max_rpm < 0.8:
                self.gearIndicator.changeState(GearIndicator.GearChange.READY)
            else:
                self.gearIndicator.changeState(GearIndicator.GearChange.STAY)
            
            self.slip.paramValue.setText("{:.2f}".format(fdp.tire_combined_slip_RL))
            self.fuel.paramValue.setText(str(fdp.fuel))
            self.distance.paramValue.setText("{:.2f}".format(fdp.dist_traveled))
            self.speed.paramValue.setText("{:.2f}".format(fdp.speed * 2.24))

            # Update the tire slip indicators
            self.slipRL.setValue(int(fdp.tire_combined_slip_RL * 10))
            self.slipRR.setValue(int(fdp.tire_combined_slip_RR * 10))

    
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
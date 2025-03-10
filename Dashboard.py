from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from ParamWidgets import TireSlipWidget, ParamWidget

import socket
import time
from fdp import ForzaDataPacket
import select
import yaml
import typing

from enum import Enum

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)  # Set to non blocking, so thread can be terminated without socket blocking forever
sock.bind(('', 1337))
timeout = 2

"""
Holds the configuration options and preferences for the dashboard that adjust
things like units (metric, imperial), redline % etc. These are held in an external
yaml configuration file which is read and used to update the config object
either when the program is first started, or when the user changes and closes
the settings widget.
"""
dashConfig: dict = None
dashConfigFilePath = "config/dashboardConfig.yaml"

"""
Holds possible parameters names, units and conversion factors. Is updated
once when the program starts, or when the user changes and closes the
settings widget.
"""
paramConfig: dict = None
paramConfigFilePath = "config/paramConfig.yaml"

def updateDashConfig(configFile: str):
    """
    Reads the dashboard config file and updates the config
    settings in dashConfig
    """
    global dashConfig
    with open(configFile) as f:
        dashConfig = yaml.safe_load(f)

def updateParamConfig(configFile: str):
    """
    Reads the param config file and updates the config
    settings in paramConfig
    """
    global paramConfig
    with open(configFile) as f:
        paramConfig = yaml.safe_load(f)


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
    
    #@Slot(GearChange)
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


class Dashboard(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

        self.paramDict = {}

        self.initWidget()

    
    def initWidget(self):

        # Tries to read the dashboard config file. If unsuccessful, widgets will
        # fall back to the default units sent by Forza
        try:
            updateDashConfig(dashConfigFilePath)

            # Populate the customsable parameter widgets with the parameters from
            # the config file
            if 'parameterList' in dashConfig:
                count = 1
                for p in dashConfig['parameterList']:
                    if count > 4:  # Any more parameters will be ignored
                        break
                    pName = p.replace("_", " ")
                    self.paramDict[p] = ParamWidget(p, pName)
                    count += 1
        except:
            print("Unable to open config dash file, reverting to defaults.")
        
        try:
            updateParamConfig(paramConfigFilePath)
        except:
            print("Unable to open config param file, reverting to defaults.")
                
        self.resize(800, 480)  # Raspberry Pi touchscreen resolution
        self.maximumSize()

        self.listenButton = QtWidgets.QPushButton()
        self.slipRL = TireSlipWidget()
        self.slipRR = TireSlipWidget()
        self.gearIndicator = GearIndicator()
        self.groupWidget = QtWidgets.QWidget()
        self.centreWidget = QtWidgets.QFrame()

        self.listenButton.setCheckable(True)  # make toggleable
        self.listenButton.clicked.connect(self.toggle_loop)

        self.gearIndicator.setObjectName("gearIndicator")
        
        groupLayout = QtWidgets.QVBoxLayout()

        for w in self.paramDict.values():
            groupLayout.addWidget(w)
        
        groupLayout.setSpacing(0)
        groupLayout.setContentsMargins(0,0,0,0)
        self.groupWidget.setLayout(groupLayout)

        centreLayout = QtWidgets.QVBoxLayout(self)
        centreLayout.addWidget(self.gearIndicator)
        centreLayout.addWidget(self.groupWidget)
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

    """Updates all the widgets
    """
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
            
            
            # Update the customisable widgets
            # Matches the user's chosen units (imperial, metric etc) to values stored
            # in the param config file and does any conversions or formatting before
            # sending the value to the widget to display
            for p, w in self.paramDict.items():
                w: ParamWidget
                val = getattr(fdp, p, 0)
                dp = 2
                
                if p in paramConfig:
                    config: dict = paramConfig[p]
                    units: str = dashConfig["units"]
                    if "units" in config:
                        if units in config["units"]:
                            val *= config["factor"][units]
                    dp = config.get("dp", 2)  # Decimal places is 2 if not specified
                fs = "{:." + str(dp) + "f}"
                val = fs.format(val)
                w.update(val)

            # Update the tire slip indicators
            self.slipRL.setValue(int(fdp.tire_combined_slip_RL * 10))
            self.slipRR.setValue(int(fdp.tire_combined_slip_RR * 10))

    """ Starts/stops listening for Forza UDP packets
    """
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
            
            self.worker.collected.connect(self.onCollected)  # Update the widgets every time a packet is collected
            self.worker.finished.connect(self.loop_finished)  # do something in the gui when the worker loop ends

            self.worker.finished.connect(self.thread.quit)  # tell the thread it's time to stop running
            self.worker.finished.connect(self.worker.deleteLater)  # have worker mark itself for deletion
            self.thread.finished.connect(self.thread.deleteLater)  # have thread mark itself for deletion
            # make sure those last two are connected to themselves or you will get random crashes
            self.thread.start()
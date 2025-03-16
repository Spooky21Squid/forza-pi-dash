from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from ParamWidgets import TireSlipWidget, ParamWidget, AccelBrakeWidget, TireWidget, FuelWidget, IntervalWidget

import logging
import socket
from fdp import ForzaDataPacket
import select
import yaml
from enum import Enum
from math import floor


logging.basicConfig(level=logging.INFO)
port = None


"""
Holds the configuration options and preferences for the dashboard that adjust
things like units (metric, imperial), redline % etc. These are held in an external
yaml configuration file which is read and used to update the config object
either when the program is first started, or when the user changes and closes
the settings widget (not currently implemented).
"""
dashConfig: dict = None
dashConfigFilePath = "../config/dashboardConfig.yaml"

"""
Holds possible parameters names, units and conversion factors. Is updated
once when the program starts, or when the user changes and closes the
settings widget (not currently implemented).
"""
paramConfig: dict = None
paramConfigFilePath = "../config/paramConfig.yaml"

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

# Tries to read the parameter config file
try:
    updateParamConfig(paramConfigFilePath)
except:
    logging.info("Unable to open {}, reverting to defaults.".format(paramConfigFilePath))

# Tries to read the dash config file and set the port to receive forza UDP packets
try:
    updateDashConfig(dashConfigFilePath)
    port = dashConfig.get("port", None)
except:
    logging.info("Unable to open {}, reverting to defaults.".format(dashConfigFilePath))
    port = 1337  # A default port


# Initialises the socket that listens for packets
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(0)  # Set to non blocking, so thread can be terminated without socket blocking forever
sock.bind(('', port))
timeout = 1


class Worker(QObject):
    """
    Listens for incoming forza UDP packets and communicates to QWidgets when
    a packet is collected
    """
    finished = Signal()
    collected = Signal(bytes)

    @Slot()
    def __init__(self):
        super(Worker, self).__init__()
        self.working = True

    def work(self):
        logging.info("Started listening...")
        while self.working:
            try:
                ready = select.select([sock], [], [], timeout)
                if ready[0]:
                    data, address = sock.recvfrom(1024)
                    logging.debug('received {} bytes from {}'.format(len(data), address))
                    self.collected.emit(data)
            except BlockingIOError:
                logging.info("Could not listen to {}, trying again...".format(address))
                
        self.finished.emit()


class GearIndicator(QtWidgets.QLCDNumber):
    """
    Represents the central colour changing gear indicator
    """
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
    
    # Used to determine the background colour
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
    """
    The parent widget for the dashboard, containing all the logic for updating the widgets
    """
    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

        self.paramDict = {}

        # Stores the % fuel left over the last 4 laps - used to collect an average and display as the fuel per lap.
        # When the first packet is collected, all indexes are initialised with the current fuel level.
        self.fuelLevelHistory = [0, 0, 0, 0]

        # The last received packet as a fdp object
        self.lastPacket: ForzaDataPacket = None

        self.initWidget()
    
    def getAverageFuelUsage(self):
        """Gets the average fuel usage over the last 3 laps using the fuelLevelHistory list"""

        totalUsed = 0
        lapCount = 0

        for i in range(1, 4):
            used = self.fuelLevelHistory[i - 1] - self.fuelLevelHistory[i]
            if used > 0:
                lapCount += 1
                totalUsed += used

        if totalUsed == 0:
            return 0
        
        return totalUsed / lapCount

    def initWidget(self):

        # Tries to read the dashboard config file. If unsuccessful, widgets will
        # fall back to the default units sent by Forza
        try:
            # Populate the customisable parameter widgets with the parameters from
            # the config file
            if 'parameterList' in dashConfig:
                count = 1
                for p in dashConfig['parameterList']:
                    p: dict
                    if count > 4:  # Any more parameters will be ignored to save space
                        break
                    if paramConfig:
                        pName = paramConfig.get(p).get("label")
                    self.paramDict[p] = ParamWidget(p, pName)
                    count += 1
                while count <= 4:
                    # Populate the rest of the grid with blank widgets if there are less than 4
                    self.paramDict[str(count)] = ParamWidget("", "", "")
                    count += 1
        except:
            #logging.info("Unable to open {}, reverting to defaults.".format(dashConfigFilePath))
            pass

        self.resize(800, 480)  # Raspberry Pi touchscreen resolution

        # Start button on the top left
        self.listenButton = QtWidgets.QPushButton("Start")
        self.listenButton.setCheckable(True)  # make toggleable
        self.listenButton.clicked.connect(self.toggle_loop)
        self.listenButton.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        
        # Settings button (not currently implemented - see the config files)
        self.settingsButton = QtWidgets.QPushButton("Settings")
        self.settingsButton.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        self.positionWidget = ParamWidget("race_pos", "Pos")
        self.lapWidget = ParamWidget("lap_no", "Lap")
        self.distanceWidget = ParamWidget("dist_traveled", "Dist")
        self.slipRL = TireSlipWidget()
        self.slipRR = TireSlipWidget()
        
        # Central widget containing brake, gear and accel displays
        self.gearAccelBrakeWidget = QtWidgets.QFrame()
        gearAccelBrakeLayout = QtWidgets.QHBoxLayout()
        gearAccelBrakeLayout.setSpacing(0)
        gearAccelBrakeLayout.setContentsMargins(0,0,0,0)
        self.accelWidget = AccelBrakeWidget()
        self.accelWidget.setObjectName("accelWidget")
        self.brakeWidget = AccelBrakeWidget()
        self.brakeWidget.setObjectName("brakeWidget")
        self.gearIndicator = GearIndicator()
        self.gearIndicator.setObjectName("gearIndicator")
        gearAccelBrakeLayout.addWidget(self.brakeWidget)
        gearAccelBrakeLayout.addWidget(self.gearIndicator)
        gearAccelBrakeLayout.addWidget(self.accelWidget)
        self.gearAccelBrakeWidget.setLayout(gearAccelBrakeLayout)

        self.centreWidget = QtWidgets.QFrame()
        self.lastLapTimeWidget = ParamWidget("last_lap_time", "Last")
        self.bestLapTimeWidget = ParamWidget("best_lap_time", "Best")

        self.interval = IntervalWidget()
        self.interval.setProperty("style", True)
        self.interval.setAlignment(Qt.AlignCenter)

        self.tireWidget = TireWidget()

        self.fuelWidget = FuelWidget()

        centreLayout = QtWidgets.QGridLayout()
        centreLayout.setSpacing(3)
        centreLayout.setContentsMargins(0,0,0,0)

        # Left side of the dashboard
        centreLayout.addWidget(self.listenButton, 0, 0)
        centreLayout.addWidget(self.settingsButton, 0, 1)
        centreLayout.addWidget(self.positionWidget, 1, 0)
        centreLayout.addWidget(self.lapWidget, 1, 1)
        centreLayout.addWidget(self.distanceWidget, 2, 0, 1, 2)
        centreLayout.addWidget(self.tireWidget, 3, 0, -1, 2)

        # Centre
        centreLayout.addWidget(self.gearAccelBrakeWidget, 0, 2, 3, 1)
        row = 3
        for w in self.paramDict.values():
            w.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
            centreLayout.addWidget(w, row, 2)
            row += 1
        del row

        # Right Side of the dashboard
        centreLayout.addWidget(self.lastLapTimeWidget, 0, 3, 1, 2)
        centreLayout.addWidget(self.bestLapTimeWidget, 1, 3, 1, 2)
        centreLayout.addWidget(self.interval, 2, 3, 1, 2)
        centreLayout.addWidget(self.fuelWidget, 3, 3, -1, -1)

        self.centreWidget.setLayout(centreLayout)

        mainLayout = QtWidgets.QHBoxLayout(self)
        mainLayout.addWidget(self.slipRL)
        mainLayout.addWidget(self.centreWidget)
        mainLayout.addWidget(self.slipRR)
        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0,0,0,0)
        self.setLayout(mainLayout)

        # Progress bars start out with some initial values just to test they work
        #self.slipRL.setValue(50)
        #self.brakeWidget.setValue(50)
        #self.accelWidget.setValue(50)
    
    def loop_finished(self):
        logging.info("Finished listening.")

        # Reset the tire slip indicator bars
        self.slipRR.reset()
        self.slipRL.reset()

        # Reset the accel/brake bars
        self.accelWidget.reset()
        self.brakeWidget.reset()

    def onCollected(self, data):
        """
        Updates all the widgets in the dashboard after a packet is collected
        """
        logging.debug("Received Data")
        fdp = ForzaDataPacket(data)
        if fdp.is_race_on:
            self.gearIndicator.display(fdp.gear)

            # Changes the gear indicator colour based on percentages from dashConfig
            redlinePercent = dashConfig.get("redlinePercent", 85) * 0.01
            readyPercent = dashConfig.get("readyPercent", 75) * 0.01

            if fdp.current_engine_rpm / fdp.engine_max_rpm >= redlinePercent:
                self.gearIndicator.changeState(GearIndicator.GearChange.CHANGE)
            elif fdp.current_engine_rpm / fdp.engine_max_rpm >= readyPercent and fdp.current_engine_rpm / fdp.engine_max_rpm < redlinePercent:
                self.gearIndicator.changeState(GearIndicator.GearChange.READY)
            else:
                self.gearIndicator.changeState(GearIndicator.GearChange.STAY)
             
            # Updates the customisable widgets
            # Matches the user's chosen units (imperial, metric etc) to values stored
            # in the param config file and does any conversions or formatting before
            # sending the value to the widget to display.
            for p, w in self.paramDict.items():
                w: ParamWidget
                val = getattr(fdp, p, 0)
                dp = 2
                
                if p in paramConfig:
                    config: dict = paramConfig[p]
                    units: str = dashConfig["units"]
                    if "units" in config:
                        if units in config["units"]:
                            if units != "default":
                                val *= config["factor"][units]
                    dp = config.get("dp", 2)  # Decimal places is 2 if not specified
                fs = "{:." + str(dp) + "f}"
                val = fs.format(val)
                w.update(val)

            # Update the tire slip indicators
            self.slipRL.setValue(int(fdp.tire_combined_slip_RL * 10))
            self.slipRR.setValue(int(fdp.tire_combined_slip_RR * 10))

            # Update Pos, Lap, and Dist widgets
            pos = fdp.race_pos
            self.positionWidget.update(pos)

            lap = fdp.lap_no
            self.lapWidget.update(lap)

            dist = self.convertUnits(self.distanceWidget.paramName, fdp.dist_traveled)
            self.distanceWidget.update(dist)

            # last lap
            lastLap = fdp.last_lap_time  # in seconds
            minutes, seconds = divmod(lastLap, 60)
            mseconds = str(seconds - floor(seconds))  # gets us the decimal part
            mseconds = mseconds[2:5]
            self.lastLapTimeWidget.update("{}:{}.{}".format(int(minutes), int(seconds), mseconds))
            
            # best lap
            bestLap = fdp.best_lap_time  # in seconds
            minutes, seconds = divmod(bestLap, 60)
            mseconds = str(seconds - floor(seconds))  # gets us the decimal part
            mseconds = mseconds[2:5]
            self.bestLapTimeWidget.update("{}:{}.{}".format(int(minutes), int(seconds), mseconds))

            # interval
            # All the logic for maintaining the interval is found in the Interval class
            self.interval.update(fdp)
            currentInterval = self.interval.getInterval()
            logging.debug("Interval: {:.10f}, Lap Dist: {:.5f}, Lap Time: {:.5f}".format(currentInterval, self.interval.currentPoint[0], self.interval.currentPoint[1]))
            minutes, seconds = divmod(abs(currentInterval), 60)
            mseconds = str(seconds - floor(seconds))  # gets us the decimal part
            mseconds = mseconds[2:5]
            sign = "+"
            if currentInterval < 0:
                sign = "-"
            self.interval.setText("{}{}.{}".format(sign, int(seconds), mseconds))

            # accel and brake progress bars
            self.accelWidget.setValue(fdp.accel)
            self.brakeWidget.setValue(fdp.brake)

            # Tire wear and heat
            tireWidgets = (
                self.tireWidget.fl,
                self.tireWidget.fr,
                self.tireWidget.rl,
                self.tireWidget.rr
            )
            
            tireOrder = ("FL", "FR", "RL", "RR")

            # get the tire temparature configs
            blueTemp = dashConfig.get("tireTempBlue", 160)
            yellowTemp = dashConfig.get("tireTempYellow", 240)
            redTemp = dashConfig.get("tireTempRed", 330)
            
            for tire, widget in zip(tireOrder, tireWidgets):
                widget.wear.setText("{}%".format(int(getattr(fdp, "tire_wear_{}".format(tire)) * 100)))
                tireTemp = getattr(fdp, "tire_temp_{}".format(tire))
                tireTemp = float(self.convertUnits("tire_wear_{}".format(tire), tireTemp))
                if tireTemp <= blueTemp:
                    widget.tireIcon.setStyleSheet("border: 3px solid blue;")
                elif tireTemp >= redTemp:
                    widget.tireIcon.setStyleSheet("border: 3px solid red;")
                elif tireTemp >= yellowTemp:
                    widget.tireIcon.setStyleSheet("border: 3px solid yellow;")
                else:
                    widget.tireIcon.setStyleSheet("border: 3px solid green;")
            
            # Fuel widget
            fuel = fdp.fuel
            self.fuelWidget.fuelLevel.update(self.convertUnits("fuel", fuel * 100))
            lapsLeft = 0
            usage = self.getAverageFuelUsage()

            # If on a new lap, update the fuel values
            if self.lastPacket and fdp.lap_no != self.lastPacket.lap_no:
                self.fuelLevelHistory.pop(0)
                self.fuelLevelHistory.append(fuel)
                usage = self.getAverageFuelUsage()

                # update estimated fuel used per lap
                self.fuelWidget.fuelPerLap.update(self.convertUnits("fuel", usage * 100))

            # update estimated laps left
            if usage:
                lapsLeft =  fuel / usage
                self.fuelWidget.lapsLeft.update(self.convertUnits("fuel", lapsLeft))

            # Display small pit warning if laps left <= 1
            if ((lapsLeft <= 1 and usage) or fuel == 0) and dashConfig.get("pitWarning"):
                self.fuelWidget.pitNow.setStyleSheet("background-color: lightgrey;")
            else:
                self.fuelWidget.pitNow.setStyleSheet("background-color: black;")
            self.lastPacket = fdp

    def convertUnits(self, paramName: str, paramValue):
        """
        Converts a parameter from the default units to the current
        units using the conversion factors found in paramConfig and
        returns as a string

        paramName is the forza-returned name
        paramValue is the default forza-returned value
        """
        global paramConfig
        global dashConfig

        if paramName in paramConfig:
            config: dict = paramConfig[paramName]
            units: str = dashConfig["units"]
            if "units" in config:
                if units in config["units"]:
                    if units != "default":
                        paramValue *= config["factor"][units]
            dp = config.get("dp", 2)  # Decimal places is 2 if not specified
        fs = "{:." + str(dp) + "f}"
        val = fs.format(paramValue)
        return val

    @Slot()
    def toggle_loop(self, checked):
        """
        Starts/stops listening for Forza UDP packets
        """
        if not checked:
            self.worker.working = False
            logging.debug("Worker set to false")
            self.thread.quit()
        else:
            logging.debug("Thread started")
            self.worker = Worker()  # a new worker
            self.thread = QThread()  # a new thread to listen for packets
            self.worker.moveToThread(self.thread)
            # move the worker into the thread, do this first before connecting the signals
            self.thread.started.connect(self.worker.work)
            # begin worker object's loop when the thread starts running
            self.worker.collected.connect(self.onCollected)  # Update the widgets every time a packet is collected
            self.worker.finished.connect(self.loop_finished)  # Do something when the worker loop ends

            self.worker.finished.connect(self.thread.quit)  # Tell the thread to stop running
            self.worker.finished.connect(self.worker.deleteLater)  # Have worker mark itself for deletion
            self.thread.finished.connect(self.thread.deleteLater)  # Have thread mark itself for deletion
            # Make sure those last two are connected to themselves or you will get random crashes
            self.thread.start()
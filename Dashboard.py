from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QObject, Signal, Slot, QThread
from ParamWidgets import TireSlipWidget, ParamWidget, AccelBrakeWidget, TireWidget, FuelWidget

import logging
import socket
from fdp import ForzaDataPacket
import select
import yaml
from enum import Enum
from math import floor, sqrt


logging.basicConfig(level=logging.INFO)

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

# Calculates the interval (time delta) between the player at their current position
# and a previous lap (typically the best lap). Does this by:
#  - Getting the player's current position as an xz coord and the cur lap time
#    (Don't need Y as it's a vertical measure)
#  - Getting the comparison lap's position and time data as a list of tuples of
#    the form (position_x, position_z, cur_lap_time)
#  - Finds the data point with the nearest x/z coord to the player's current position
#    and compares the difference in current lap times
#  - Returns that as the interval
#
# Finding the closest coordinate
# - Brute force it - for each data point, calculate the euclidean distance to
#   the current position and keep a record of the one with the minumum distance
#
# - Store it differently - for each data point, instead of storing the x and z positions,
#   calculate the euclidean distance to a generic point in space, store them as
#   (euc_distance, cur_lap_time), and order them based on that distance.
#   Then, find the player's current position's euc distance to that same generic
#   point and get the closest data point. If multiple points have the same euc
#   distance, return the one with the closest cur_lap_time.
#
# - Brute force it for now - its just a prototype after all
#   Performance will decrease for longer laps as it will have to search more to find the closest point
def calculateInterval(intervals: list, current: tuple):
    # current = (position_x, position_z, cur_lap_time)
    closestEucDist = 9999999999999
    closestPoint = None

    for interval in intervals:
        eucDist = euclideanDistance(current[0], current[1], interval[0], interval[1])
        if eucDist < closestEucDist:
            closestEucDist = eucDist
            closestPoint = interval
    
    return current[2] - closestPoint[2]  # Negative is faster, positive is slower


def euclideanDistance(x1, y1, x2, y2):
    """Calculates the euclidean distance for a pair of 2-dimensional vectors"""

    xDist = x2 - x1
    yDist = y2 - y1
    total = xDist**2 + yDist**2
    total = sqrt(total)
    return total


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
                    logging.debug('received {} bytes from {}'.format(len(data), address))
                    self.collected.emit(data)
                #data, address = sock.recvfrom(1024)
                #print('received {} bytes from {}'.format(len(data), address))
                #time.sleep(0.05)
                #self.collected.emit(data)
            except BlockingIOError:
                logging.info("Could not listen to {}, trying again...".format(address))
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

        # Used for testing - does nothing with a new packet if true, to slow
        # down updating the display
        self.discardData = False

        self.paramDict = {}

        # Stores the % fuel left over the last 4 laps
        # When the first packet is collected, all indexes are initialised with
        # the current fuel level.
        self.fuelLevelHistory = [0, 0, 0, 0]

        # The last received packet as a fdp object
        self.lastPacket: ForzaDataPacket = None

        # List of tuples containing (position_x, position_z, cur_lap_time)
        # Compared to calculate the interval
        # (Should automatically be sorted by time, but no guarantee (UDP unreliability) but lets just assume.)
        self.lastLapIntervals = []
        self.currentLapIntervals = []

        self.initWidget()
    

    def getAverageFuelUsage(self):
        """Gets the average fuel usage over the last 3 laps"""

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

        try:
            updateParamConfig(paramConfigFilePath)
        except:
            logging.info("Unable to open {}, reverting to defaults.".format(paramConfigFilePath))

        # Tries to read the dashboard config file. If unsuccessful, widgets will
        # fall back to the default units sent by Forza
        try:
            updateDashConfig(dashConfigFilePath)

            # Populate the customisable parameter widgets with the parameters from
            # the config file
            if 'parameterList' in dashConfig:
                count = 1
                for p in dashConfig['parameterList']:
                    p: dict
                    if count > 4:  # Any more parameters will be ignored
                        break
                    if paramConfig:
                        pName = paramConfig.get(p).get("label")
                    #pName = p.replace("_", " ")
                    self.paramDict[p] = ParamWidget(p, pName)
                    count += 1
                while count <= 4:
                    self.paramDict[str(count)] = ParamWidget("", "", "")  # Populate the rest of the grid with blank widgets
                    count += 1
        except:
            logging.info("Unable to open {}, reverting to defaults.".format(dashConfigFilePath))

        self.resize(800, 480)  # Raspberry Pi touchscreen resolution

        self.listenButton = QtWidgets.QPushButton("Start")
        self.listenButton.setCheckable(True)  # make toggleable
        self.listenButton.clicked.connect(self.toggle_loop)
        self.listenButton.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        
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

        self.interval = QtWidgets.QLabel("0.000")  # Calculated interval estimate
        self.interval.setProperty("style", True)
        self.interval.setAlignment(Qt.AlignCenter)

        self.tireWidget = TireWidget()

        self.fuelWidget = FuelWidget()

        centreLayout = QtWidgets.QGridLayout()
        centreLayout.setSpacing(3)
        centreLayout.setContentsMargins(0,0,0,0)

        # Left side
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

        # Right Side
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

        # Just to test
        self.slipRL.setValue(50)
        self.brakeWidget.setValue(50)
        self.accelWidget.setValue(50)
    
    def loop_finished(self):
        logging.info("Finished listening.")

        ## Reset the tire slip indicator bars
        self.slipRR.reset()
        self.slipRL.reset()

    """Updates all the widgets
    """
    def onCollected(self, data):
        logging.debug("Received Data")
        if self.discardData:
            self.discardData = not self.discardData
            return
        self.discardData = not self.discardData
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

            # Update Pos, Lap, Dist, last and current lap time widgets
            pos = fdp.race_pos
            self.positionWidget.update(pos)

            lap = fdp.lap_no
            self.lapWidget.update(lap)

            dist = self.convertUnits(self.distanceWidget.paramName, fdp.dist_traveled)
            self.distanceWidget.update(dist)

            # last lap
            lastLap = fdp.last_lap_time  # in seconds
            minutes, seconds = divmod(lastLap, 60)
            seconds = seconds
            mseconds = str(seconds - floor(seconds))  # gets us the decimal part
            mseconds = mseconds[2:5]
            self.lastLapTimeWidget.update("{}:{}.{}".format(int(minutes), int(seconds), mseconds))
            
            # best lap
            bestLap = fdp.best_lap_time  # in seconds
            minutes, seconds = divmod(bestLap, 60)
            seconds = seconds
            mseconds = str(seconds - floor(seconds))  # gets us the decimal part
            mseconds = mseconds[2:5]
            self.bestLapTimeWidget.update("{}:{}.{}".format(int(minutes), int(seconds), mseconds))

            # interval
            if self.lastPacket and fdp.lap_no != self.lastPacket.lap_no:
                if fdp.best_lap_time == self.lastPacket.best_lap_time:
                    self.lastLapIntervals = self.currentLapIntervals
                self.currentLapIntervals = []

            currentPoint = (fdp.position_x, fdp.position_z, fdp.cur_lap_time)
            self.currentLapIntervals.append(currentPoint)

            # If there is a best lap logged
            if len(self.lastLapIntervals):
                interval = calculateInterval(self.lastLapIntervals, currentPoint)  # in seconds
                #logging.info("Interval: {}".format(interval))
                minutes, seconds = divmod(abs(interval), 60)
                mseconds = str(seconds - floor(seconds))  # gets us the decimal part
                mseconds = mseconds[2:5]
                sign = "+"
                if interval < 0:
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
                #palette = widget.tireIcon.palette()
                if tireTemp <= blueTemp:
                    #palette.setColor(widget.foregroundRole(), QColor(0, 0, 255))
                    widget.tireIcon.setStyleSheet("border: 3px solid blue;")
                elif tireTemp >= redTemp:
                    #palette.setColor(widget.foregroundRole(), QColor(255, 0, 0))
                    widget.tireIcon.setStyleSheet("border: 3px solid red;")
                elif tireTemp >= yellowTemp:
                    #palette.setColor(widget.foregroundRole(), QColor(255, 255, 0))
                    widget.tireIcon.setStyleSheet("border: 3px solid yellow;")
                else:
                    #palette.setColor(widget.foregroundRole(), QColor(255, 255, 255))
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
            if lapsLeft <= 1 and usage:
                self.fuelWidget.pitNow.setStyleSheet("background-color: lightgrey;")
            else:
                self.fuelWidget.pitNow.setStyleSheet("background-color: black;")




            self.lastPacket = fdp




    def convertUnits(self, paramName: str, paramValue):
        """
        Converts a parameter from the default units to the current
        units and returns as a string
        """
        global paramConfig
        global dashConfig

        if paramName in paramConfig:
            config: dict = paramConfig[paramName]
            units: str = dashConfig["units"]
            if "units" in config:
                if units in config["units"]:
                    paramValue *= config["factor"][units]
            dp = config.get("dp", 2)  # Decimal places is 2 if not specified
        fs = "{:." + str(dp) + "f}"
        val = fs.format(paramValue)
        return val

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
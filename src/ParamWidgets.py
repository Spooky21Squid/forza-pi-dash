from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Slot, Signal
from fdp import ForzaDataPacket
from enum import Enum
from math import floor
import logging


class ParamWidget(QtWidgets.QFrame):
    """
    A compound widget that simply Displays the name of a parameter, and the value of
    that parameter next to it. Eg. tire_temp_FL displays the tempatarure
    of the front left tire.

    Attributes
    ----------

    - paramName: The name of the parameter in the forza data packet
    - paramLabel: The user-friendly label for the widget to display
    - paramValue: The value of the parameter
    """

    def __init__(self, paramName: str, paramLabel: str, paramValue = "0", stretch = 50):
        super().__init__()

        self.paramName = paramName
        self.paramLabel = QtWidgets.QLabel(paramLabel)
        self.paramLabel.setObjectName("paramLabel")
        self.paramValue = QtWidgets.QLabel(paramValue)
        self.paramValue.setObjectName("paramValue")

        self.paramLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #self.paramValue.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.paramLabel, stretch)
        layout.addWidget(self.paramValue, 100 - stretch)
        self.setLayout(layout)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""

        self.paramValue.setText("0")
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """
        Updates the widget's value with an updated value from the forza data packet, and
        the widget's parameter label
        """

        newValue = getattr(fdp, self.paramName)
        formattedValue = self.format(newValue, dashConfig)
        self.paramValue.setText(formattedValue)
    
    def format(self, value, dashConfig: dict) -> str:
        """
        Converts a parameter from its forza data packet format to a
        new format suitable for displaying on the dashboard. Eg. the
        best_lap_time parameter is sent as a time in seconds, but will be converted
        to a minutes : seconds . milliseconds format.

        Parameters
        ----------

        - value: The value of the parameter to be formatted
        - dashConfig: The config dict containing the dashboard settings
        """
        
        paramName = self.paramName
        result = None

        match paramName:
            case "race_pos":
                result = str(int(value))
            case "lap_no":
                result = str(int(value))
            case "dist_traveled":
                units = dashConfig["distanceUnits"]
                if units == "metric":
                    result = value * 0.001  # metres to kilometres
                else:
                    result = value * 0.0006213712  # metres to miles
                result = "{:.3f}".format(result)
            case "last_lap_time" | "best_lap_time" | "cur_lap_time":
                minutes, seconds = divmod(value, 60)
                mseconds = str(seconds - floor(seconds))  # gets us the decimal part
                mseconds = mseconds[2:5]
                result = "{}:{}.{}".format(int(minutes), int(seconds), mseconds)
            case "fuel":
                result = "{:.2f}".format(value * 100)
            case "laps_left" | "fuel_per_lap":
                result = "{:.2f}".format(value)
            case _:  # Couldn't find that parameter
                result = str(value)
        
        return result


class SpeedWidget(QtWidgets.QFrame):
    """
    A widget that displays the speed of the player as their chosen units
    """

    def __init__(self):
        super().__init__()

        #self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.value = QtWidgets.QLabel("0")
        self.units = QtWidgets.QLabel("mph")

        self.value.setObjectName("speedValue")
        self.units.setObjectName("speedUnits")

        self.units.setAlignment(Qt.AlignCenter)
        self.value.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.value)
        layout.addWidget(self.units)
        self.setLayout(layout)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        
        self.value.setText("0")
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """
        Updates the speed and units with an updated value from the forza data packet
        and the chosen units from dashConfig
        """

        newValue = fdp.speed
        units = dashConfig["speedUnits"]

        if units == "imperial":
            self.units.setText("mph")
            self.value.setText(str(int(newValue * 2.24)))
        else:
            self.units.setText("kmh")
            self.value.setText(str(int(newValue * 3.6)))


class SingleTireWidget(QtWidgets.QFrame):
    """Represents a single tire temp/wear combo inside the large tire widget"""

    # Which tire it represents on the car (eg. FL = front left)
    class Corner(Enum):
        FL = 0
        FR = 1
        RL = 2
        RR = 3

    def __init__(self, corner: Corner):
        super().__init__()

        self.corner = corner
        
        # Shows the temperature by changing the border colour of the box
        self.tireIcon = QtWidgets.QFrame(frameShape=QtWidgets.QFrame.Box)
        self.tireIcon.setObjectName("tireTemp")

        # Shows tire wear as a percentage
        self.wear = QtWidgets.QLabel("0%")
        self.wear.setAlignment(Qt.AlignCenter)
        self.wear.setObjectName("tireWear")

        # Position the tire icon and wear % on different sides of the widget
        # depending on orientation (left or right tire). Makes no difference
        # to the widgets function.
        layout = QtWidgets.QHBoxLayout(self)
        if corner is self.Corner.FL or corner is self.Corner.RL:
            layout.addWidget(self.wear)
            layout.addWidget(self.tireIcon)
        else:
            layout.addWidget(self.tireIcon)
            layout.addWidget(self.wear)
        self.setLayout(layout)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        
        self.wear.setText("0%")
        self.tireIcon.setStyleSheet("border: 3px solid #44e520;")
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        tireWearParam = ""
        tireTempParam = ""

        if self.corner is self.Corner.FL:
            tireWearParam = "tire_wear_FL"
            tireTempParam = "tire_temp_FL"
        elif self.corner is self.Corner.FR:
            tireWearParam = "tire_wear_FR"
            tireTempParam = "tire_temp_FR"
        elif self.corner is self.Corner.RL:
            tireWearParam = "tire_wear_RL"
            tireTempParam = "tire_temp_RL"
        else:
            tireWearParam = "tire_wear_RR"
            tireTempParam = "tire_temp_RR"
        
        tireWear = getattr(fdp, tireWearParam)
        tireTemp = getattr(fdp, tireTempParam)
        
        # Update the tire wear and temperature with values from
        # the fdp, and using temp values from dashConfig

        self.wear.setText("{}%".format(int(tireWear * 100)))

        blueTemp = dashConfig["tireTempBlue"]
        yellowTemp = dashConfig["tireTempYellow"]
        redTemp = dashConfig["tireTempRed"]

        if tireTemp <= blueTemp:
            self.tireIcon.setStyleSheet("border: 3px solid blue;")
        elif tireTemp >= redTemp:
            self.tireIcon.setStyleSheet("border: 3px solid red;")
        elif tireTemp >= yellowTemp:
            self.tireIcon.setStyleSheet("border: 3px solid yellow;")
        else:
            self.tireIcon.setStyleSheet("border: 3px solid green;")


class CompoundTireWidget(QtWidgets.QFrame):
    """The widget holding all the individual tire widgets"""

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QGridLayout()

        self.fl = SingleTireWidget(SingleTireWidget.Corner.FL)
        self.fr = SingleTireWidget(SingleTireWidget.Corner.FR)
        self.rl = SingleTireWidget(SingleTireWidget.Corner.RL)
        self.rr = SingleTireWidget(SingleTireWidget.Corner.RR)

        layout.addWidget(self.fl, 0, 0)
        layout.addWidget(self.fr, 0, 1)
        layout.addWidget(self.rl, 1, 0)
        layout.addWidget(self.rr, 1, 1)

        self.setLayout(layout)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        self.fl.reset()
        self.fr.reset()
        self.rl.reset()
        self.rr.reset()
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """Updates each single tire widget with their tire wear and temps"""
        self.fl.update(fdp, dashConfig)
        self.fr.update(fdp, dashConfig)
        self.rl.update(fdp, dashConfig)
        self.rr.update(fdp, dashConfig)


class TireSlipWidget(QtWidgets.QProgressBar):
    """Displays the amount of tire slip of one wheel as a vertical bar"""
    def __init__(self, tire:str):
        """
        Parameters
        ----------
        tire : str
            The name of the parameter that the widget will read from
            the data packet. Eg. tire_combined_slip_RR
        """
        super().__init__()

        self.tire = tire
        self.setMaximum(100)
        self.setMinimum(5)
        self.setTextVisible(False)
        self.setOrientation(Qt.Vertical)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        self.setValue(0)
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """Updates the tire slip widget with a new value"""
        value = getattr(fdp, self.tire, 0)
        self.setValue(int(value * 10))


class GearWidget(QtWidgets.QLabel):
    """
    The central colour changing gear indicator
    """

    def __init__(self):
        super().__init__()
        self.setText("0")
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(30)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        self.setText("0")
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """
        Updates the number and colour of the gear indicator using the
        rpm % limits set in the config settings
        """

        self.setText(str(int(fdp.gear)))

        rpm = fdp.current_engine_rpm
        maxrpm = fdp.engine_max_rpm

        if rpm == 0 or maxrpm == 0:
            return

        ratio = rpm / maxrpm
        
        redlinePercent = dashConfig.get("redlinePercent", 85) * 0.01
        readyPercent = dashConfig.get("readyPercent", 75) * 0.01

        if ratio >= redlinePercent:
            self.setStyleSheet("color: red")
        elif ratio >= readyPercent and ratio < redlinePercent:
            self.setStyleSheet("color: yellow")
        else:
            self.setStyleSheet("color: white")


class IntervalWidget(QtWidgets.QFrame):
    """Maintains all the data related to the interval"""

    def __init__(self):
        super().__init__()

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.interval = QtWidgets.QLabel("0.000")
        self.label = QtWidgets.QLabel("delta")

        self.interval.setObjectName("intervalValue")
        self.label.setObjectName("intervalLabel")

        self.interval.setAlignment(Qt.AlignCenter)
        self.label.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.interval)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.bestLap = None  # The best lap as recorded by this object, not by Forza
        self.currentLap = -2
        self.syncLap = -1  # The lap the player needs to reach to begin recording intervals
        self.currentPoint = None
        self.distanceFactor = 0  # The distance to take away to get current lap distance
        
        # Stores a list of (lapDistance:float, lapTime:float) points, where lapDistance
        # is the distance traveled during that lap in metres, and lapTime is the current
        # lap time recorded at that distance in seconds
        self.bestLapPoints = list()
        self.currentLapPoints = list()
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        self.interval.setText("0.000")
        self.bestLap = None
        self.currentLap = -2
        self.syncLap = -1
        self.currentPoint = None
        self.distanceFactor = 0
        self.bestLapPoints = list()
        self.currentLapPoints = list()
        self.interval.setStyleSheet("color: white;")

    def insertPoint(self):
        """
        Inserts the current point into the currentLapPoints list. If the distance
        recorded is less or equal than the previous packet, it is ignored. If it is
        negative (hasn't crossed the line after starting the race), it is ignored.
        """
        if len(self.currentLapPoints) == 0 or self.currentPoint[0] > self.currentLapPoints[-1][0] or self.currentPoint[0] < 0:
            self.currentLapPoints.append(self.currentPoint)
    
    def updateInterval(self):
        """
        Updates the current interval by comparing the current point's lap time to
        the closest point's lap time in the bestLapTime list
        """

        if len(self.bestLapPoints) == 0:
            return

        currentTime = self.currentPoint[1]
        currentDistance = self.currentPoint[0]

        # Search for the closest best lap point
        # Could use binary search but for now just use linear

        bestDifference = 9999999999999
        bestPointIndex = 0

        currentIndex = 0
        while currentIndex < len(self.bestLapPoints):
            bestLapDist, bestLapTime = self.bestLapPoints[currentIndex]
            currentDifference = abs(bestLapDist - currentDistance)
            if currentDifference <= bestDifference:
                bestDifference = currentDifference
                bestPointIndex = currentIndex
                currentIndex += 1
            else:
                break
        
        bestPoint = self.bestLapPoints[bestPointIndex]
        interval = currentTime - bestPoint[1] # negative is faster

        minutes, seconds = divmod(abs(interval), 60)
        mseconds = str(seconds - floor(seconds))  # gets us the decimal part
        mseconds = mseconds[2:5]
        sign = "+"
        if interval < 0:
            sign = "-"
        self.interval.setText("{}{}.{}".format(sign, int(seconds), mseconds))

        if interval > 0:
            self.interval.setStyleSheet("color: #d54242;")  # Red
        elif interval < 0:
            self.interval.setStyleSheet("color: #62d542;")  # Green
        else:
            self.interval.setStyleSheet("color: white;")
    
    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """
        Updates the Interval object with the latest packet
        
        To display an accurate interval, an entire uninterrupted lap needs to be
        recorded as a baseline. So if a player starts the dashboard in the middle of
        a lap, that lap is ignored, and the next lap is used as a baseline. This means
        the interval will appear on the 2nd lap.
        """
        
        playerLap = int(fdp.lap_no)
        currentLapTime = fdp.cur_lap_time
        currentDistance = fdp.dist_traveled
        lapDistance = currentDistance - self.distanceFactor
        self.currentPoint = (lapDistance, currentLapTime)

        if playerLap == self.currentLap:
            # Log the current point

            self.insertPoint()
            self.updateInterval()

        elif playerLap == self.currentLap + 1:
            
            # If the player stopped listening on the prev lap and started again on the next lap,
            # making the time logs inconsistent with the game
            if currentLapTime > 1:
                self.currentLap = -1
                self.currentLapPoints = []
                self.syncLap = playerLap + 1
                return

            # just began a new lap, update the lap counter and compare it to best lap
            # Doesn't use the game's best lap - uses an internally tracked best lap which
            # can be a dirty lap. This is to allow the dashboard to be started mid race
            # and still display an interval, and also to allow a useful interval to be
            # displayed when using non-forza-clean limits (eg. some Tora races), but this
            # can be changed

            # If player just set a new best lap
            if self.bestLap is None or self.bestLap <= 0 or fdp.last_lap_time < self.bestLap:
                logging.debug("Interval: Best Lap! {}".format(fdp.last_lap_time))
                self.bestLapPoints = self.currentLapPoints.copy()
                self.bestLap = fdp.last_lap_time
            else: # If player didn't set a best lap
                logging.debug("Interval: New Lap. {}".format(fdp.last_lap_time))
            self.currentLapPoints.clear()

            # update the distance factor and thus the current point's distance
            self.distanceFactor = fdp.dist_traveled
            lapDistance = currentDistance - self.distanceFactor
            self.currentPoint = (lapDistance, currentLapTime)

            self.insertPoint()
            self.currentLap += 1
            self.updateInterval()

        else:  # player lap is not consistent with self.currentLap (eg. started recording in the middle of a session)
            if playerLap == self.syncLap:
                logging.debug("Interval: Synced Laps")
                # player has reached new sync lap, update object and start recording
                self.currentLapPoints.clear()

                # update the distance factor and thus the current point's distance
                self.distanceFactor = fdp.dist_traveled
                lapDistance = currentDistance - self.distanceFactor
                self.currentPoint = (lapDistance, currentLapTime)

                self.insertPoint()
                self.currentLap = self.syncLap
                self.updateInterval()
            else:  # Keep ignoring the lap times until the player reaches a new lap
                self.syncLap = playerLap + 1


class AlertWidget(QtWidgets.QLabel):
    """
    A widget for an alert on the dashboard, either pit now or
    not racing alert
    """

    def __init__(self, text: str):
        super().__init__(text)
        sp = QtWidgets.QSizePolicy()
        sp.setRetainSizeWhenHidden(True)
        sp.setHorizontalPolicy(QtWidgets.QSizePolicy.Expanding)
        sp.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
        self.setSizePolicy(sp)
        self.setAlignment(Qt.AlignCenter)
    
    @Slot()
    def showHide(self, hide: bool):
        """
        Shows or hides the alert

        Parameters
        ----------

        - hide: True to hide the alert, False to show the alert
        """
        
        if hide:
            self.hide()
        else:
            self.show()


class FuelWidget(QtWidgets.QFrame):
    """Contains all the fuel information widgets"""

    enoughFuel = Signal(bool)  # False if low fuel

    def __init__(self):
        super().__init__()

        self.fuelLevelHistory = None
        self.lastLap = -3

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        # How much space the fuel labels and values get
        widgetStretch = 63

        self.fuelLevel = ParamWidget("fuel", "FUEL LEVEL", stretch=widgetStretch)
        self.fuelPerLap = ParamWidget("fuel_per_lap", "FUEL PER LAP", stretch=widgetStretch)
        self.lapsLeft = ParamWidget("laps_left", "LAPS LEFT", stretch=widgetStretch)

        layout.addWidget(self.fuelLevel)
        layout.addWidget(self.fuelPerLap)
        layout.addWidget(self.lapsLeft)

        self.setLayout(layout)
    
    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        
        self.fuelLevel.reset()
        self.fuelPerLap.reset()
        self.lapsLeft.reset()
        self.fuelLevelHistory = None
        self.lastLap = -3
    
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

    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """Updates all the fuel widgets"""

        self.fuelLevel.update(fdp, dashConfig)

        fuel = fdp.fuel
        lapsLeft = 0

        # If on a new lap, update the fuel values
        if fdp.lap_no != self.lastLap:
            self.lastLap = fdp.lap_no
            if self.fuelLevelHistory is None:
                self.fuelLevelHistory = [fuel for i in range(4)]
            else:
                self.fuelLevelHistory.pop(0)
                self.fuelLevelHistory.append(int(fuel * 10000) / 100)
            usage = self.getAverageFuelUsage()

            # update estimated fuel used per lap
            fdp.fuel_per_lap = usage
            self.fuelPerLap.update(fdp, dashConfig)
        else:
            usage = self.getAverageFuelUsage()

        # update estimated laps left
        if usage:
            lapsLeft =  (fuel / usage) * 100
            fdp.laps_left = lapsLeft
            self.lapsLeft.update(fdp, dashConfig)
            
            if lapsLeft <= 1:
                self.enoughFuel.emit(False)
            else:
                self.enoughFuel.emit(True)


class lastLapTimeWidget(ParamWidget):

    @Slot()
    def reset(self):
        """Resets the widget back to its starting state with no information"""
        self.paramValue.setText("0")
        self.paramLabel.setStyleSheet("color: white;")
        self.paramValue.setStyleSheet("color: white;")

    @Slot()
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """
        Overrides the ParamWidget's update method with extra function to
        compare this time to the best time, and change its colour
        """

        newValue = getattr(fdp, self.paramName)
        formattedValue = self.format(newValue, dashConfig)
        self.paramValue.setText(formattedValue)

        bestLapTime = getattr(fdp, "best_lap_time")
        if newValue == 0 or bestLapTime == 0:
            return
        
        if newValue > bestLapTime:
            self.paramLabel.setStyleSheet("color: #d54242;")  # Red
            self.paramValue.setStyleSheet("color: #d54242;")
        else:
            self.paramLabel.setStyleSheet("color: #62d542;")  # Green
            self.paramValue.setStyleSheet("color: #62d542;")
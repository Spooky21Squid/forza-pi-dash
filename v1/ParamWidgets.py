from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from enum import Enum
from fdp import ForzaDataPacket
import logging


class ParamWidget(QtWidgets.QFrame):
    """
    A compund widget that simply Displays the name of a parameter, and the value of
    that parameter next to it. Eg. tire_temp_FL displays the tempatarure
    of the front left tire. They can be simply organised vertically
    or horizontally, like blocks.

    paramName: The configuration name of the parameter
    paramLabel: The user-friendly label for the widget
    paramValue: The value the parameter currently holds
    """
    def __init__(self, paramName: str, paramLabel: str, paramValue = "0"):
        super().__init__()

        self.paramName = paramName
        self.paramLabel = QtWidgets.QLabel(paramLabel)
        self.paramValue = QtWidgets.QLabel(paramValue)

        self.paramLabel.setAlignment(Qt.AlignCenter)
        self.paramValue.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.paramLabel)
        layout.addWidget(self.paramValue)
        self.setLayout(layout)
    
    def update(self, value):
        """
        Updates the displayed parameter's value
        """
        self.paramValue.setText(str(value))


class TireSlipWidget(QtWidgets.QProgressBar):
    """Displays the amount of tire slip of one wheel as a vertical bar"""
    def __init__(self):
        super().__init__()
        self.initWidget()

    def initWidget(self):
        self.setMaximum(100)
        self.setMinimum(5)
        self.setTextVisible(False)
        self.setOrientation(Qt.Vertical)


class AccelBrakeWidget(QtWidgets.QProgressBar):
    """Displays the amount of accel/brake input as a vertical bar"""
    def __init__(self):
        super().__init__()
        self.initWidget()

    def initWidget(self):
        self.setMaximum(255)
        self.setMinimum(0)
        self.setTextVisible(False)
        self.setOrientation(Qt.Vertical)
        self.setFixedWidth(12)


class SingleTireWidget(QtWidgets.QFrame):
    """Represents a single tire temp/wear combo inside the large tire widget"""

    # Does it represent a tire on the left or right side of the car
    class Orientation(Enum):
        LEFT = 0
        RIGHT = 1

    def __init__(self, orientation: Orientation = Orientation.LEFT):
        super().__init__()
        
        self.tireIcon = QtWidgets.QFrame(frameShape=QtWidgets.QFrame.Box)
        self.tireIcon.setObjectName("tire")
        self.wear = QtWidgets.QLabel("0%")

        self.wear.setAlignment(Qt.AlignCenter)

        # Position the tire icon and wear % on different sides of the widget
        # depending on orientation (left or right tire). Makes no difference
        # to the widgets function.
        layout = QtWidgets.QHBoxLayout(self)
        if orientation is self.Orientation.LEFT:
            layout.addWidget(self.wear)
            layout.addWidget(self.tireIcon)
        else:
            layout.addWidget(self.tireIcon)
            layout.addWidget(self.wear)
        self.setLayout(layout)


class TireWidget(QtWidgets.QFrame):
    """The widget holding all the individual tire widgets"""
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QGridLayout()

        self.fl = SingleTireWidget()
        self.fr = SingleTireWidget(SingleTireWidget.Orientation.RIGHT)
        self.rl = SingleTireWidget()
        self.rr = SingleTireWidget(SingleTireWidget.Orientation.RIGHT)

        layout.addWidget(self.fl, 0, 0)
        layout.addWidget(self.fr, 0, 1)
        layout.addWidget(self.rl, 1, 0)
        layout.addWidget(self.rr, 1, 1)

        self.setLayout(layout)


class FuelWidget(QtWidgets.QFrame):
    """Contains all the fuel information widgets and pit now message"""
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout()

        self.fuelLevel = ParamWidget("fuel", "Fuel Level")
        self.fuelLevel.setObjectName("fuel")
        self.fuelLevel.paramLabel.setAlignment(Qt.AlignVCenter)
        self.fuelLevel.paramValue.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.fuelPerLap = ParamWidget("fpl", "Fuel Per Lap")
        self.fuelPerLap.setObjectName("fuel")
        self.fuelPerLap.paramLabel.setAlignment(Qt.AlignVCenter)
        self.fuelPerLap.paramValue.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lapsLeft = ParamWidget("lapsLeft", "Laps Left")
        self.lapsLeft.setObjectName("fuel")
        self.lapsLeft.paramLabel.setAlignment(Qt.AlignVCenter)
        self.lapsLeft.paramValue.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Background color set to black by default so user cannot see it, but the
        # layout stays the same
        self.pitNow = QtWidgets.QLabel("PIT THIS LAP")
        self.pitNow.setAlignment(Qt.AlignCenter)
        self.pitNow.setObjectName("pitNowSmall")

        layout.addWidget(self.fuelLevel)
        layout.addWidget(self.fuelPerLap)
        layout.addWidget(self.lapsLeft)
        layout.addWidget(self.pitNow)

        self.setLayout(layout)


class IntervalWidget(QtWidgets.QLabel):
    """Maintains all the data related to the interval"""

    def __init__(self):
        super().__init__("0.000")
        self.bestLap = None  # The best lap as recorded by this object, not by Forza
        self.currentLap = -1
        self.syncLap = 0  # The lap the player needs to reach to begin recording intervals
        self.currentPoint = None
        self.distanceFactor = 0  # The distance to take away to get current lap distance
        
        # Stores a list of (lapDistance:float, lapTime:float) points, where lapDistance
        # is the distance traveled during that lap in metres, and lapTime is the current
        # lap time recorded at that distance in seconds
        self.bestLapPoints = list()
        self.currentLapPoints = list()

        self.interval: float = None  # The current up to date interval

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
            self.interval = 0
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
        self.interval = currentTime - bestPoint[1]  # negative is Faster
        
    def update(self, fdp: ForzaDataPacket):
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
            logging.debug("Interval update: {:.2f} (Cur Lap)".format(self.interval))

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
            logging.debug("Interval update: {:.2f} (New Lap)".format(self.interval))

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
                logging.debug("Interval update: {:.2f} (Sync)".format(self.interval))
            else:  # Keep ignoring the lap times until the player reaches a new lap
                self.syncLap = playerLap + 1
        
    def getInterval(self):
        """Returns the most up to date interval based on all collected data points.
        If there is not enough data to calculate an interval, return 0."""
        if self.interval:
            return self.interval
        else:
            return 0


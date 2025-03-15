from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from enum import Enum
from fdp import ForzaDataPacket
import logging

"""A compund widget that simply Displays the name of a parameter, and the value of
that parameter next to it. Eg. tire_temp_FL displays the tempatarure
of the front left tire. They can be simply organised vertically
or horizontally, like blocks.

Individual parameters with complex requirements such as
number formatting or metric/imperial conversion should
inherit and extend this class.

paramName: The configuration name of the parameter
paramLabel: The user-friendly label for the widget
paramValue: The value the parameter currently holds"""
class ParamWidget(QtWidgets.QFrame):
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
    
    """ Updates the displayed parameter's value. Override this
    method to perform any conversion/formatting"""
    def update(self, value):
        self.paramValue.setText(str(value))


"""Displays the amount of tire slip of one wheel as a vertical bar"""
class TireSlipWidget(QtWidgets.QProgressBar):
    def __init__(self):
        super().__init__()
        self.initWidget()

    def initWidget(self):
        self.setMaximum(100)
        self.setMinimum(5)
        self.setTextVisible(False)
        self.setOrientation(Qt.Vertical)


class AccelBrakeWidget(QtWidgets.QProgressBar):
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
    """
    Maintains all the data related to the interval.
    """

    def __init__(self):
        super().__init__("0.000")
        self.bestLap = None  # The best lap as recorded by this object, not by Forza
        self.currentLap = -1
        self.syncLap = 0  # The lap the player needs to reach to begin recording intervals
        self.currentPoint = None
        self.accuracy = 20
        self.distanceFactor = 0
        
        # Stores a list of lapDistance:int - lapTime:float points, where lapDistance
        # is the distance traveled during that lap in metres (the distance to the start
        # of the mini sector), and lapTime is the current lap time recorded at
        # that distance in seconds
        self.bestLapPoints = dict()
        self.currentLapPoints = dict()

        self.interval: float = None

    def insertPoint(self):
        """
        Inserts the current point into the currentLapPoints list.
        """

        # Ignores the point if the mini sector entry already has a value
        miniSector, remainder = divmod(int(self.currentPoint[0]), self.accuracy)
        #miniSector = int(self.currentPoint[0]) % self.accuracy
        if not self.currentLapPoints.get(miniSector):
            self.currentLapPoints[miniSector] = self.currentPoint[1]
    
    def updateInterval(self):
        """
        Updates the current interval by comparing the current point's lap time to
        the best lap's corresponding sector time
        """

        currentTime = self.currentPoint[1]  # In seconds
        miniSector, remainder = divmod(int(self.currentPoint[0]), self.accuracy)
        #miniSector = int(self.currentPoint[0]) % self.accuracy
        bestSectorTime = self.bestLapPoints.get(miniSector, 0)

        if bestSectorTime == 0:
            self.interval = 0
        else:
            self.interval = currentTime - bestSectorTime  # Negative is faster 

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
            # Log the current point if the player is at the start of a new mini sector

            if int(lapDistance) % self.accuracy == 0:
                self.insertPoint()
                self.updateInterval()
                logging.info("Interval update: {:.2f} (Cur Lap)".format(self.interval))

        elif playerLap == self.currentLap + 1:
            
            # If the player stopped listening on the prev lap and started again on the next lap
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
            if self.bestLap is None or fdp.last_lap_time < self.bestLap:  # If player just set a new best lap
                logging.info("Interval: Best Lap! {}".format(fdp.last_lap_time))
                self.bestLapPoints = self.currentLapPoints.copy()
                self.bestLap = fdp.last_lap_time
            else: # If player didn't set a best lap
                logging.info("Interval: New Lap. {}".format(fdp.last_lap_time))
            self.currentLapPoints.clear()

            # update the distance factor and thus the current point's distance
            self.distanceFactor = fdp.dist_traveled
            lapDistance = currentDistance - self.distanceFactor
            self.currentPoint = (lapDistance, currentLapTime)

            self.insertPoint()
            self.currentLap += 1
            self.updateInterval()
            logging.info("Interval update: {:.2f} (New Lap)".format(self.interval))

        else:  # player lap is not consistent with self.currentLap (eg. started recording in the middle of a session)
            if playerLap == self.syncLap:
                logging.info("Interval: Synced Laps")
                # player has reached new sync lap, update object and start recording
                self.currentLapPoints.clear()

                # update the distance factor and thus the current point's distance
                self.distanceFactor = fdp.dist_traveled
                lapDistance = currentDistance - self.distanceFactor
                self.currentPoint = (lapDistance, currentLapTime)

                self.insertPoint()
                self.currentLap = self.syncLap
                self.updateInterval()
                logging.info("Interval update: {:.2f} (Sync)".format(self.interval))
            else:  # Keep ignoring the lap times until the player reaches a new lap
                self.syncLap = playerLap + 1
        
    def getInterval(self):
        """Returns the most up to date interval based on all collected data points.
        If there is not enough data to calculate an interval, return 0."""
        if self.interval:
            return self.interval
        else:
            return 0


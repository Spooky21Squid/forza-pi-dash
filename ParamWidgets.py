from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from enum import Enum

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

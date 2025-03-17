from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Slot
from fdp import ForzaDataPacket
from enum import Enum


class ParamWidget(QtWidgets.QFrame):
    """
    A compund widget that simply Displays the name of a parameter, and the value of
    that parameter next to it. Eg. tire_temp_FL displays the tempatarure
    of the front left tire.

    Attributes
    ----------

    - paramName: The name of the parameter in the forza data packet
    - paramLabel: The user-friendly label for the widget to display
    - paramValue: The value of the parameter
    """

    def __init__(self, paramName: str, paramLabel: str, paramValue = "0"):
        super().__init__()

        self.paramName = paramName
        self.paramLabel = QtWidgets.QLabel(paramLabel)
        self.paramValue = QtWidgets.QLabel(paramValue)

        self.paramLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        #self.paramValue.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.paramLabel)
        layout.addWidget(self.paramValue)
        self.setLayout(layout)
    
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
            case _:  # Couldn't find that parameter
                result = str(value)
        
        return result


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
        #self.tireIcon.setObjectName("tire")

        # Shows tire wear as a percentage
        self.wear = QtWidgets.QLabel("0%")
        self.wear.setAlignment(Qt.AlignCenter)

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
    def update(self, fdp: ForzaDataPacket, dashConfig: dict):
        """Updates the tire slip widget with a new value"""
        value = getattr(fdp, self.tire, 0)
        self.setValue(int(value * 10))

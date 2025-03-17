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

        #self.paramLabel.setAlignment(Qt.AlignCenter)
        #self.paramValue.setAlignment(Qt.AlignCenter)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.paramLabel)
        layout.addWidget(self.paramValue)
        self.setLayout(layout)
    
    @Slot()
    def update(self, fdp: ForzaDataPacket):
        """
        Updates the displayed parameter's value with an updated value
        from the forza data packet
        """
        
        newValue = getattr(fdp, self.paramName)
        self.paramValue.setText(str(newValue))


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
        self.tireIcon.setObjectName("tire")

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
    def update(self, fdp: ForzaDataPacket):
        paramName = ""
        if self.corner is self.Corner.FL:
            paramName = "tire_wear_FL"
        elif self.corner is self.Corner.FR:
            paramName = "tire_wear_FR"
        elif self.corner is self.Corner.RL:
            paramName = "tire_wear_RL"
        else:
            paramName = "tire_wear_RR"
        
        # Update the tire wear and temperature with values from
        # the fdp, and using temp values from dashConfig


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
    def update(self, fdp: ForzaDataPacket):
        """Updates the tire slip widget with a new value"""
        value = getattr(fdp, self.tire, 0)
        self.setValue(int(value * 10))

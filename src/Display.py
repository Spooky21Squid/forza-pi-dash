from PySide6 import QtWidgets
from PySide6.QtCore import Signal

from ParamWidgets import TireSlipWidget, ParamWidget, CompoundTireWidget, GearWidget, SpeedWidget, IntervalWidget, AlertWidget, FuelWidget, lastLapTimeWidget

from fdp import ForzaDataPacket


class DisplayWidget(QtWidgets.QFrame):
    """Displays the main dashboard"""

    updateSignal = Signal(ForzaDataPacket, dict)

    def __init__(self):
        super().__init__()

        # Define the layouts ----------------------

        mainLayout = QtWidgets.QHBoxLayout()  # For the left tire slip, rest of dash, and right tire slip
        dashLayout = QtWidgets.QVBoxLayout()  # Sits in the middle of the tire slip bars
        buttonLayout = QtWidgets.QHBoxLayout()  # Horizontal bar of buttons at the top
        middleLayout = QtWidgets.QHBoxLayout()  # Contains the left, centre and right layouts
        posLapDistLayout = QtWidgets.QVBoxLayout()  # Vertical group of pos lap and dist widgets
        lapTimesLayout = QtWidgets.QVBoxLayout()  # Vertical group of lap time widgets
        leftLayout = QtWidgets.QVBoxLayout()  # Left column, grouping poslapdist and tire widgets
        centreLayout = QtWidgets.QVBoxLayout()  # Centre column, grouping gear, speed and delta
        rightLayout = QtWidgets.QVBoxLayout()  # Right column, grouping time and fuel

        # Styling the layouts ---------------------------

        mainLayout.setSpacing(0)
        mainLayout.setContentsMargins(0,0,0,0)

        # replace below with spacer widgets instead
        centreLayout.setSpacing(10)
        rightLayout.setSpacing(10)
        leftLayout.setSpacing(10)

        # Define the widgets ---------------------------

        # Top row of buttons
        self.listenButton = QtWidgets.QPushButton("START")
        self.listenButton.setCheckable(True)  # Make toggleable
        self.settingsButton = QtWidgets.QPushButton("SETTINGS")
        self.resetButton = QtWidgets.QPushButton("RESET")

        # Tire slip bars
        self.slipRight = TireSlipWidget("tire_combined_slip_RR")
        self.slipLeft = TireSlipWidget("tire_combined_slip_RL")

        # Position, lap number and distance widgets
        self.position = ParamWidget("race_pos", "POSITION")
        self.lap = ParamWidget("lap_no", "LAP")
        self.distance = ParamWidget("dist_traveled", "DISTANCE")

        # Tire wear and temp compound widget
        self.tires = CompoundTireWidget()
        
        # Gear indicator, speed and interval
        self.gear = GearWidget()
        self.speed = SpeedWidget()
        self.interval = IntervalWidget()

        # Not racing indicator
        self.notRacing = AlertWidget("NOT RACING")
        self.notRacing.setObjectName("notRacing")

        # Lap time widgets
        timesStretch = 40
        self.bestLapTime = ParamWidget("best_lap_time", "BEST", stretch=timesStretch)
        self.lastLapTime = lastLapTimeWidget("last_lap_time", "LAST", stretch=timesStretch)
        self.currentLapTime = ParamWidget("cur_lap_time", "CURRENT", stretch=timesStretch)

        # Fuel widget
        self.fuel = FuelWidget()

        # Small pit now alert box
        self.pitAlert = AlertWidget("PIT THIS LAP")
        self.pitAlert.setObjectName("pitAlert")

        # Connect all the widgets --------------------------

        self.updateSignal.connect(self.slipRight.update)
        self.updateSignal.connect(self.slipLeft.update)

        self.updateSignal.connect(self.position.update)
        self.updateSignal.connect(self.lap.update)
        self.updateSignal.connect(self.distance.update)

        self.updateSignal.connect(self.tires.update)

        self.updateSignal.connect(self.gear.update)
        self.updateSignal.connect(self.speed.update)
        self.updateSignal.connect(self.interval.update)

        self.updateSignal.connect(self.bestLapTime.update)
        self.updateSignal.connect(self.lastLapTime.update)
        self.updateSignal.connect(self.currentLapTime.update)

        self.updateSignal.connect(self.fuel.update)
        self.fuel.enoughFuel.connect(self.pitAlert.showHide)

        self.resetButton.clicked.connect(self.slipRight.reset)
        self.resetButton.clicked.connect(self.slipLeft.reset)
        self.resetButton.clicked.connect(self.position.reset)
        self.resetButton.clicked.connect(self.lap.reset)
        self.resetButton.clicked.connect(self.distance.reset)
        self.resetButton.clicked.connect(self.tires.reset)
        self.resetButton.clicked.connect(self.gear.reset)
        self.resetButton.clicked.connect(self.speed.reset)
        self.resetButton.clicked.connect(self.interval.reset)
        self.resetButton.clicked.connect(self.bestLapTime.reset)
        self.resetButton.clicked.connect(self.lastLapTime.reset)
        self.resetButton.clicked.connect(self.currentLapTime.reset)
        self.resetButton.clicked.connect(self.fuel.reset)

        # Add everything to the layouts ---------------------------
        rightLayout.addLayout(lapTimesLayout, 35)
        rightLayout.addWidget(self.fuel, 35)
        rightLayout.addWidget(self.pitAlert, 30)
        
        lapTimesLayout.addWidget(self.bestLapTime)
        lapTimesLayout.addWidget(self.lastLapTime)
        lapTimesLayout.addWidget(self.currentLapTime)

        centreLayout.addWidget(self.gear, 35)
        centreLayout.addWidget(self.speed, 15)
        centreLayout.addWidget(self.interval, 15)
        centreLayout.addWidget(self.notRacing, 30)

        posLapDistLayout.addWidget(self.position)
        posLapDistLayout.addWidget(self.lap)
        posLapDistLayout.addWidget(self.distance)

        leftLayout.addLayout(posLapDistLayout, 35)
        leftLayout.addWidget(self.tires, 65)

        middleLayout.addLayout(leftLayout, 40)
        middleLayout.addLayout(centreLayout, 20)
        middleLayout.addLayout(rightLayout, 40)

        buttonLayout.addWidget(self.listenButton)
        buttonLayout.addWidget(self.settingsButton)
        buttonLayout.addWidget(self.resetButton)

        dashLayout.addLayout(buttonLayout)
        dashLayout.addLayout(middleLayout)

        mainLayout.addWidget(self.slipLeft)
        mainLayout.addLayout(dashLayout)
        mainLayout.addWidget(self.slipRight)

        # Finally set the main layout for the display
        self.setLayout(mainLayout)

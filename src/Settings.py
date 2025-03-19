from PySide6 import QtWidgets
from PySide6.QtCore import Slot, Qt
import logging

class settingsLayout(QtWidgets.QFormLayout):
    """
    The form layout for the settings tab - all the rows and widgets needed
    to display and update the dashConfig
    """

    def __init__(self):
        super().__init__()

        self.newDashConfig = dict()

        self.setSpacing(20)

        # Add widgets corresponding to the settings the user can change

        self.port = QtWidgets.QSpinBox(minimum=1025, maximum=65535)
        
        self.speedUnits = QtWidgets.QComboBox()
        self.speedUnits.addItems(["metric", "imperial"])

        self.distanceUnits = QtWidgets.QComboBox()
        self.distanceUnits.addItems(["metric", "imperial"])

        self.redlinePercent = QtWidgets.QSpinBox(maximum=100)
        self.readyPercent = QtWidgets.QSpinBox(maximum=100)

        self.tireTempBlue = QtWidgets.QSpinBox(maximum=500)
        self.tireTempYellow = QtWidgets.QSpinBox(maximum=500)
        self.tireTempRed = QtWidgets.QSpinBox(maximum=500)

        #self.pitWarning = QtWidgets.QCheckBox()

        # Connect the widgets

        self.port.valueChanged.connect(self.onUpdated)

        self.speedUnits.currentTextChanged.connect(self.onUpdated)
        self.distanceUnits.currentTextChanged.connect(self.onUpdated)

        self.redlinePercent.valueChanged.connect(self.onUpdated)
        self.readyPercent.valueChanged.connect(self.onUpdated)

        self.tireTempBlue.valueChanged.connect(self.onUpdated)
        self.tireTempYellow.valueChanged.connect(self.onUpdated)
        self.tireTempRed.valueChanged.connect(self.onUpdated)

        #self.pitWarning.checkStateChanged.connect(self.onUpdated)

        # Add the widgets to the form

        self.addRow("Port", self.port)
        self.addRow("Speed Units", self.speedUnits)
        self.addRow("Distance Units", self.distanceUnits)
        self.addRow("Redline Percent", self.redlinePercent)
        self.addRow("Ready Percent", self.readyPercent)
        self.addRow("Blue Tire Temp", self.tireTempBlue)
        self.addRow("Yellow Tire Temp", self.tireTempYellow)
        self.addRow("Red Tire Temp", self.tireTempRed)
        #self.addRow("Display Pit Warning", self.pitWarning)
    
    @Slot()
    def onUpdated(self):
        """Updates the newDashConfig every time a form's widget updates its value"""

        self.newDashConfig["port"] = self.port.value()

        self.newDashConfig["speedUnits"] = self.speedUnits.currentText()
        self.newDashConfig["distanceUnits"] = self.distanceUnits.currentText()

        self.newDashConfig["redlinePercent"] = self.redlinePercent.value()
        self.newDashConfig["readyPercent"] = self.readyPercent.value()

        self.newDashConfig["tireTempBlue"] = self.tireTempBlue.value()
        self.newDashConfig["tireTempYellow"] = self.tireTempYellow.value()
        self.newDashConfig["tireTempRed"] = self.tireTempRed.value()

        #self.newDashConfig["pitWarning"] = self.pitWarning.isChecked()
        logging.debug("Settings form updated")
        

class SettingsWidget(QtWidgets.QFrame):
    """The widget for the settings pane"""

    def __init__(self):
        super().__init__()

        # Define the layouts --------------------
        mainLayout = QtWidgets.QVBoxLayout()
        topBarLayout = QtWidgets.QHBoxLayout()  # The top bar including title, ip and close button
        self.formLayout = settingsLayout()  # The layout for the form itself

        # Define the widgets --------------------

        self.title = QtWidgets.QLabel("Settings")
        self.ip = QtWidgets.QLabel("0.0.0.0")
        self.saveButton = QtWidgets.QPushButton("Save")  # Saves settings to dashConfig and closes the settings tab
        self.cancelButton = QtWidgets.QPushButton("Cancel")  # Exits the settings button without saving anything
        
        scrollAreaContent = QtWidgets.QWidget()
        scrollAreaContent.setObjectName("settingsScrollArea")
        scrollAreaContent.setLayout(self.formLayout)

        scrollArea = QtWidgets.QScrollArea()  # Put the form in this to make it scrollable
        scrollArea.setWidget(scrollAreaContent)
        scrollArea.setWidgetResizable(True)
        scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Add everything to the layouts ---------------------

        topBarLayout.addWidget(self.title)
        topBarLayout.addWidget(self.ip)
        topBarLayout.addWidget(self.cancelButton)
        topBarLayout.addWidget(self.saveButton)

        mainLayout.addLayout(topBarLayout)
        mainLayout.addWidget(scrollArea)

        self.setLayout(mainLayout)
    
    @Slot()
    def populateForm(self, dashConfig: dict):
        """Populates the settings tab form with all the existing settings from dashConfig"""

        self.formLayout.port.setValue(int(dashConfig["port"]))

        self.formLayout.speedUnits.setCurrentText(dashConfig["speedUnits"])
        self.formLayout.distanceUnits.setCurrentText(dashConfig["distanceUnits"])

        self.formLayout.redlinePercent.setValue(int(dashConfig["redlinePercent"]))
        self.formLayout.readyPercent.setValue(int(dashConfig["readyPercent"]))

        self.formLayout.tireTempBlue.setValue(int(dashConfig["tireTempBlue"]))
        self.formLayout.tireTempYellow.setValue(int(dashConfig["tireTempYellow"]))
        self.formLayout.tireTempRed.setValue(int(dashConfig["tireTempRed"]))

        #self.formLayout.pitWarning.setChecked(dashConfig["pitWarning"])

        logging.info("Settings Loaded")

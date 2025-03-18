from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Slot, Signal
from fdp import ForzaDataPacket
from enum import Enum
from math import floor
import logging

class settingsLayout(QtWidgets.QFormLayout):
    """
    The form layout for the settings tab - all the rows and widgets needed
    to display and update the dashConfig
    """

    def __init__(self):
        super().__init__()

        self.newDashConfig = dict()

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

        self.pitWarning = QtWidgets.QCheckBox()

        # Connect the widgets

        self.port.valueChanged.connect(self.onUpdated)

        self.speedUnits.currentTextChanged.connect(self.onUpdated)
        self.distanceUnits.currentTextChanged.connect(self.onUpdated)

        self.redlinePercent.valueChanged.connect(self.onUpdated)
        self.readyPercent.valueChanged.connect(self.onUpdated)

        self.tireTempBlue.valueChanged.connect(self.onUpdated)
        self.tireTempYellow.valueChanged.connect(self.onUpdated)
        self.tireTempRed.valueChanged.connect(self.onUpdated)

        self.pitWarning.checkStateChanged.connect(self.onUpdated)

        # Add the widgets to the form

        self.addRow("Port", self.port)
        self.addRow("Speed Units", self.speedUnits)
        self.addRow("Distance Units", self.distanceUnits)
        self.addRow("Redline Percent", self.redlinePercent)
        self.addRow("Ready Percent", self.readyPercent)
        self.addRow("Blue Tire Temp", self.tireTempBlue)
        self.addRow("Yellow Tire Temp", self.tireTempYellow)
        self.addRow("Red Tire Temp", self.tireTempRed)
        self.addRow("Display Pit Warning", self.pitWarning)
    
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

        self.newDashConfig["pitWarning"] = self.pitWarning.isChecked()
        logging.info("Settings form updated")
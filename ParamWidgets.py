from PySide6 import QtWidgets
from PySide6.QtCore import Qt, QObject, Signal, Slot
from abc import ABC, abstractmethod
from enum import Enum


"""Defines the 2 types of units the dash can display"""
class Units(Enum):
    IMPERIAL = 0
    METRIC = 1
    DEFAULT = 2


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

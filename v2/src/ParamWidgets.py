from PySide6 import QtWidgets
from PySide6.QtCore import Qt, Slot
from fdp import ForzaDataPacket


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

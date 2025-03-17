from PySide6 import QtWidgets
from PySide6.QtCore import Slot, QThread, QObject, Signal

from ParamWidgets import TireSlipWidget, ParamWidget, CompoundTireWidget, GearWidget, SpeedWidget, IntervalWidget

from fdp import ForzaDataPacket

import logging
import select
import socket
from enum import Enum

class Worker(QObject):
    """
    Listens for incoming forza UDP packets and communicates to QWidgets when
    a packet is collected
    """
    finished = Signal()
    collected = Signal(bytes)

    @Slot()
    def __init__(self, port:int):
        super(Worker, self).__init__()
        self.working = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(0)  # Set to non blocking, so the thread can be terminated without the socket blocking forever
        self.socketTimeout = 1
        self.port = port

    def work(self):
        """Binds the socket and starts listening for packets"""
        self.sock.bind(('', self.port))
        logging.info("Started listening...")

        while self.working:
            try:
                ready = select.select([self.sock], [], [], self.socketTimeout)
                if ready[0]:
                    data, address = self.sock.recvfrom(1024)
                    logging.debug('received {} bytes from {}'.format(len(data), address))
                    self.collected.emit(data)
                else:
                    logging.debug("Socket timeout")
            except BlockingIOError:
                logging.info("Could not listen to {}, trying again...".format(address))
        
        # Close the socket after the player wants to stop listening, so that
        # a new socket can be created using the same port next time
        #self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        logging.info("Socket closed.")
        self.finished.emit()


class SettingsWidget(QtWidgets.QFrame):
    """The widget for the settings pane"""

    def __init__(self):
        super().__init__()

        self.closeButton = QtWidgets.QPushButton("Close")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.closeButton)
        self.setLayout(layout)


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
        leftLayout = QtWidgets.QVBoxLayout()  # Left column, grouping poslapdist and tire widgets
        centreLayout = QtWidgets.QVBoxLayout()  # Centre column, grouping gear, speed and delta
        rightLayout = QtWidgets.QVBoxLayout()  # Right column, grouping time and fuel

        # Define the widgets ---------------------------

        # Top row of buttons
        self.listenButton = QtWidgets.QPushButton("START")
        self.listenButton.setCheckable(True)  # Make toggleable
        #self.listenButton.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
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

        # Add everything to the layouts ---------------------------

        centreLayout.addWidget(self.gear)
        centreLayout.addWidget(self.speed)
        centreLayout.addWidget(self.interval)

        posLapDistLayout.addWidget(self.position)
        posLapDistLayout.addWidget(self.lap)
        posLapDistLayout.addWidget(self.distance)

        leftLayout.addLayout(posLapDistLayout)
        leftLayout.addWidget(self.tires)

        middleLayout.addLayout(leftLayout)
        middleLayout.addLayout(centreLayout)
        middleLayout.addLayout(rightLayout)

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


class Dashboard(QtWidgets.QMainWindow):
    """
    The parent widget for the dashboard which contains a stacked widget with all the
    tabs (Display, Settings) and controls the threads responsible for listening to packets
    """

    class TabIndex(Enum):
        """An Enum class to keep track of the index of different tabs in the stack widget"""
        SETTINGS = 1
        DISPLAY = 0

    updateSignal = Signal(ForzaDataPacket, dict)

    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

        self.dashConfig = dict()
        self.paramConfig = dict()

        self.ip = ""

        self.resize(800, 480)

        self.display = DisplayWidget()
        self.settings = SettingsWidget()
        self.stack = QtWidgets.QStackedWidget()
        self.stack.addWidget(self.display)
        self.stack.addWidget(self.settings)
        self.setCentralWidget(self.stack)

        # Connect the signals to change between settings and display
        self.display.settingsButton.clicked.connect(self.changeToSettingsTab)
        self.settings.closeButton.clicked.connect(self.changeToDisplayTab)

        # So the listen button triggers the thread
        self.display.listenButton.clicked.connect(self.toggle_loop)

        # Chain the update signal to the display widget's update signal
        self.updateSignal.connect(self.display.updateSignal)

    @Slot()
    def changeToSettingsTab(self):
        """Changes the current tab to the settings tab"""
        self.stack.setCurrentIndex(self.TabIndex.SETTINGS.value)
    
    @Slot()
    def changeToDisplayTab(self):
        """Changes the current tab to the display tab"""
        self.stack.setCurrentIndex(self.TabIndex.DISPLAY.value)
    
    @Slot()
    def toggle_loop(self, checked):
        """
        Starts/stops listening for Forza UDP packets
        """
        if not checked:
            # Disable the button until the thread's socket times out, and the thread is terminated
            self.display.listenButton.setEnabled(False)
            self.worker.working = False
            logging.debug("Worker set to false")
            self.thread.quit()
        else:
            logging.debug("Thread started")

            # Disable the settings and reset until player stops listening for packets
            self.display.settingsButton.setEnabled(False)
            self.display.resetButton.setEnabled(False)
            self.worker = Worker(self.dashConfig["port"])  # a new worker
            self.thread = QThread()  # a new thread to listen for packets
            self.worker.moveToThread(self.thread)
            # move the worker into the thread, do this first before connecting the signals
            self.thread.started.connect(self.worker.work)
            # begin worker object's loop when the thread starts running
            self.worker.collected.connect(self.onCollected)  # Update the widgets every time a packet is collected
            self.worker.finished.connect(self.loop_finished)  # Do something when the worker loop ends

            self.worker.finished.connect(self.thread.quit)  # Tell the thread to stop running
            self.worker.finished.connect(self.worker.deleteLater)  # Have worker mark itself for deletion
            self.thread.finished.connect(self.thread.deleteLater)  # Have thread mark itself for deletion
            # Make sure those last two are connected to themselves or you will get random crashes
            self.thread.start()

    def onCollected(self, data):
        """Called when a single UDP packet is collected. Receives the unprocessed
        packet data, transforms it into a Forza Data Packet and emits the update signal with
        that forza data packet object, and the dashboard config dictionary. If the race
        is not on, it does not emit the signal"""

        logging.debug("onCollected: Received Data")
        fdp = ForzaDataPacket(data)
        if not fdp.is_race_on:
            return
        self.updateSignal.emit(fdp, self.dashConfig)

    def loop_finished(self):
        """Called after the port is closed and the dashboard stops listening to packets"""
        logging.info("Finished listening")
        self.display.listenButton.setEnabled(True)
        self.display.settingsButton.setEnabled(True)
        self.display.resetButton.setEnabled(True)

    def updatePort(newPort:int):
        """Updates the port that listens for forza UDP packets"""
        pass

    def updateConfig(self, dashConfig:dict = None, paramConfig:dict = None):
        """Updates the dashboard's configuration"""
        
        self.dashConfig = dashConfig
        self.paramConfig = paramConfig

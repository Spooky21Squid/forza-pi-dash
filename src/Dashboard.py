from PySide6 import QtWidgets
from PySide6.QtCore import Slot, QThread, QObject, Signal, Qt

from fdp import ForzaDataPacket
from Settings import SettingsWidget
from Display import DisplayWidget

import pathlib
import yaml
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
        logging.info("Started listening on port {}".format(self.port))

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
    isRacing = Signal(bool)
    configUpdated = Signal(dict)  # Emit when dashConfig is updated

    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

        self.dashConfig = dict()

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
        self.settings.saveButton.clicked.connect(self.changeToDisplayTab)
        self.settings.cancelButton.clicked.connect(self.changeToDisplayTab)

        # So the listen button triggers the thread
        self.display.listenButton.clicked.connect(self.toggle_loop)

        # Chain the update signal to the display widget's update signal
        self.updateSignal.connect(self.display.updateSignal)

        # Show or hide the 'NOT RACING' alert based on fdp.is_race_on
        self.isRacing.connect(self.display.notRacing.showHide)

        # Update the settings tab when dashConfig is updated
        self.configUpdated.connect(self.settings.populateForm)

        self.settings.saveButton.clicked.connect(self.saveConfig)

        self.settings.fullScreenToggleButton.clicked.connect(self.toggleFullScreen)
    
    @Slot()
    def toggleFullScreen(self):
        print("In toggle fullscreen")
        if self.windowState() & Qt.WindowFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

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

            # Change the buttons back to normal
            self.display.listenButton.setStyleSheet("color: white;")
            self.display.settingsButton.setStyleSheet("color: white;")
            self.display.resetButton.setStyleSheet("color: white;")
            self.display.listenButton.setText("START")

            self.worker.working = False
            logging.debug("Worker set to false")
            self.thread.quit()
        else:
            logging.debug("Thread started")

            # Disable the settings and reset until player stops listening for packets
            self.display.settingsButton.setEnabled(False)
            self.display.resetButton.setEnabled(False)

            # Change buttons to a darker colour while listening to avoid
            # distracting the player
            self.display.listenButton.setStyleSheet("color: #3f3f3f;")
            self.display.settingsButton.setStyleSheet("color: #3f3f3f;")
            self.display.resetButton.setStyleSheet("color: #3f3f3f;")

            # Change listen button to 'stop'
            self.display.listenButton.setText("STOP")

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

        isRacing = bool(fdp.is_race_on)
        self.isRacing.emit(isRacing)

        if not fdp.is_race_on:
            return
        self.updateSignal.emit(fdp, self.dashConfig)

    def loop_finished(self):
        """Called after the port is closed and the dashboard stops listening to packets"""
        logging.info("Finished listening")
        self.display.listenButton.setEnabled(True)
        self.display.settingsButton.setEnabled(True)
        self.display.resetButton.setEnabled(True)
        self.isRacing.emit(False)

    def updatePort(newPort:int):
        """Updates the port that listens for forza UDP packets"""
        pass

    def updateConfig(self, dashConfig:dict = None):
        """Updates the dashboard's configuration"""
        
        self.dashConfig = dashConfig
        self.configUpdated.emit(self.dashConfig)

    @Slot()
    def saveConfig(self):
        """Updates the dashConfig with new values from the settings tab, and saves
        them into a yaml file"""

        newSettings = self.settings.formLayout.newDashConfig

        for key, value in newSettings.items():
            self.dashConfig[key] = value
        
        # Save dashConfig to the yaml file
        parentDir = pathlib.Path(__file__).parent.parent.resolve()
        dashConfigPath = parentDir / pathlib.Path("config") / pathlib.Path("dashConfig.yaml")

        with open(dashConfigPath, "w") as file:
            yaml.dump(self.dashConfig, file)
        
        logging.info("Saved settings to file")

    def updateIP(self, ip:str):
        """Updates the IP Address displayed on the settings page"""
        self.ip = ip
        self.settings.ip.setText(ip)

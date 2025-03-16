from PySide6 import QtWidgets
from PySide6.QtCore import Slot, QThread, QObject, Signal

import logging
import select
import socket

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


class Dashboard(QtWidgets.QFrame):
    """
    The parent widget for the dashboard, containing all the logic for updating the widgets
    """
    def __init__(self):
        super().__init__()

        self.worker = None
        self.thread = None

        self.dashConfig = dict()
        self.paramConfig = dict()

        self.resize(800, 480)

        self.listenButton = QtWidgets.QPushButton("Start")
        self.listenButton.setCheckable(True)  # Make toggleable
        self.listenButton.clicked.connect(self.toggle_loop)
        #self.listenButton.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.listenButton)
        self.setLayout(layout)

    @Slot()
    def toggle_loop(self, checked):
        """
        Starts/stops listening for Forza UDP packets
        """
        if not checked:
            self.worker.working = False
            logging.debug("Worker set to false")
            self.thread.quit()
        else:
            logging.debug("Thread started")
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
        """Called when a single UDP packet is collected"""
        logging.debug("onCollected: Received Data")

    def loop_finished(self):
        """Called after the port is closed and the dashboard stops listening to packets"""
        logging.info("Finished listening")

    def updatePort(newPort:int):
        """Updates the port that listens for forza UDP packets"""
        pass

    def updateConfig(self, dashConfig:dict = None, paramConfig:dict = None):
        """Updates the dashboard's configuration"""
        
        # Dummy update config for now
        newDashConfig = dict()
        newDashConfig["port"] = 1337
        self.dashConfig = newDashConfig

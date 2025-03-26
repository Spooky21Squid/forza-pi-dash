import sys
from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Qt
from MainWindow import MainWindow
import socket
import pathlib
import yaml
import logging

"""
The main file to set up and run the forza pi dashboard.

Gets the ip, checks all config files are present and then runs the Qt app.

Make sure to install all the required packages from requirements.txt, and make sure
all config files are present and well-formed.
"""

logging.basicConfig(level=logging.INFO)

def getIP():
    """Returns the local IP address as a string. If an error is encountered while trying to
    establish a connection, it will return None."""

    ip = None

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 1337))
            ip = s.getsockname()[0]
            s.close()
    except:
        return None
    
    return str(ip)

def run(ip: str, dashConfig:dict, style:str):
    app = QtWidgets.QApplication(sys.argv)

    app.setOverrideCursor(Qt.BlankCursor)

    # Add and check the custom fonts
    id = QtGui.QFontDatabase.addApplicationFont(str(fontPath))
    logging.debug("Font id: {}".format(id))
    families = QtGui.QFontDatabase.applicationFontFamilies(id)
    logging.debug("Font families: {}".format(families))

    db = MainWindow()
    db.updateConfig(dashConfig)
    db.updateIP(ip)
    db.show()
    
    if style != "":
        app.setStyleSheet(style)

    sys.exit(app.exec())

if __name__ == "__main__":
    ip = getIP()
    logging.info("IP Address: {}".format(ip))

    parentDir = pathlib.Path(__file__).parent.parent.resolve()

    # Custom font file path
    fontPath = parentDir / pathlib.Path("assets") / pathlib.Path("Audiowide-Regular.ttf")

    # Tries to read the config files
    dashConfigPath = parentDir / pathlib.Path("config") / pathlib.Path("dashConfig.yaml")
    dashConfig = None

    try:
        with open(dashConfigPath) as f:
            dashConfig = yaml.safe_load(f)
    except FileNotFoundError:
        logging.info("Unable to open dashConfig.yaml")
        exit(0)
    
    if dashConfig is None:
        logging.info("dashConfig.yaml is empty")
        exit(0)
    
    # Tries to read the stylesheets
    stylesheetsPath = parentDir / pathlib.Path("stylesheets")
    style = ""
    for sheet in stylesheetsPath.glob("*.qss"):
        with open(sheet, "r") as f:
            style += f.read() + "\n\n"


    run(ip, dashConfig, style)
    
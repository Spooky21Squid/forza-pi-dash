import sys
from PySide6 import QtWidgets
from Dashboard import Dashboard

"""
The main file to run the forza pi dashboard.

Make sure to install all the required packages from requirements.txt, and make sure
all config files are present and well-formed.
"""


def run():
    app = QtWidgets.QApplication(sys.argv)
    db = Dashboard()
    db.show()

    # Add multiple stylesheets in the order they need to be concatonated
    stylesheets = ["../stylesheets/Dashboard.qss"]
    style = ""

    for sheet in stylesheets:
        with open(sheet, "r") as f:
            style += f.read() + "\n\n"
    
    app.setStyleSheet(style)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
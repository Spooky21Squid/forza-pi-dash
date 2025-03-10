import sys
from PySide6 import QtCore, QtWidgets
from Dashboard import Dashboard


def run():
    app = QtWidgets.QApplication(sys.argv)
    db = Dashboard()
    db.show()

    # Add multiple stylesheets in the order they need to be concatonated
    stylesheets = ["stylesheets/Dashboard.qss"]
    style = ""

    for sheet in stylesheets:
        with open(sheet, "r") as f:
            style += f.read() + "\n\n"
    
    app.setStyleSheet(style)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
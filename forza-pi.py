import sys
from PySide6 import QtCore, QtWidgets
from Dashboard import Dashboard


def run():
    app = QtWidgets.QApplication(sys.argv)
    db = Dashboard()
    db.show()

    with open("Dashboard.qss", "r") as f:
        _style = f.read()
        app.setStyleSheet(_style)

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
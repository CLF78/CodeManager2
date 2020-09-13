import globalstuff
from PyQt5.QtCore import QPoint, QRect


def Half(isright=False):
    win = globalstuff.mainWindow.mdi.currentSubWindow()
    if win:
        pos = QPoint(globalstuff.mainWindow.mdi.width() // 2 if isright else 0, 0)
        rect = QRect(0, 0, globalstuff.mainWindow.mdi.width() // 2, globalstuff.mainWindow.mdi.height())
        win.setGeometry(rect)
        win.move(pos)


def TileHorizontal():
    pos = QPoint(0, 0)
    for window in globalstuff.mainWindow.mdi.subWindowList():
        rect = QRect(0, 0, globalstuff.mainWindow.mdi.width() // len(globalstuff.mainWindow.mdi.subWindowList()), globalstuff.mainWindow.mdi.height())
        window.setGeometry(rect)
        window.move(pos)
        pos.setX(pos.x() + window.width())


def TileVertical():
    pos = QPoint(0, 0)
    for window in globalstuff.mainWindow.mdi.subWindowList():
        rect = QRect(0, 0, globalstuff.mainWindow.mdi.width(), globalstuff.mainWindow.mdi.height() // len(globalstuff.mainWindow.mdi.subWindowList()))
        window.setGeometry(rect)
        window.move(pos)
        pos.setY(pos.y() + window.height())


def MinimizeAll():
    for window in globalstuff.mainWindow.mdi.subWindowList():
        window.showMinimized()


def CloseAll():
    for window in globalstuff.mainWindow.mdi.subWindowList():
        window.close()

import os
import urllib.request

import globalstuff
from PyQt5 import QtWidgets


def DownloadError():
    msgbox = QtWidgets.QMessageBox()
    msgbox.setWindowTitle('Title Database Missing')
    msgbox.setText("The Title Database (wiitdb.txt) is missing. Do you want to download it?")
    msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    ret = msgbox.exec_()
    if ret == QtWidgets.QMessageBox.Yes:
        return DownloadTitles()
    else:
        return False


def DownloadTitles():
    try:
        with urllib.request.urlopen('https://www.gametdb.com/wiitdb.txt?LANG=EN') as src, open(globalstuff.wiitdb, 'wb') as dst:
            dst.write(src.read())
        return True
    except:
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle('Download Error')
        msgbox.setText("There was an error during the database download. Retry?")
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        ret = msgbox.exec_()
        if ret == QtWidgets.QMessageBox.Yes:
            DownloadTitles()
        else:
            return False


def TitleLookup(gid):
    """
    Looks up the game name for the given game id in the title database txt
    """
    # First, check the file is still here
    if os.path.exists(globalstuff.wiitdb):
        with open(globalstuff.wiitdb, 'rb') as f:
            while True:
                try:  # Read the line, split it and check the game id. If it matches, return the game name
                    line = next(f).decode('utf-8', 'ignore').split(' = ')
                    if line[0] == gid:
                        return line[1]
                except StopIteration:  # We've reached EOF
                    return 'Unknown Game'
    else:
        # Ask the user if they want to download the database
        retry = DownloadError()
        if retry:
            TitleLookup(gid)  # Try again
        else:
            return 'Unknown Game'  # Gave up, RIP

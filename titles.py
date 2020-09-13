import os
import urllib.request

import globalstuff
from PyQt5 import QtWidgets


def DownloadError():
    msgbox = QtWidgets.QMessageBox.question(globalstuff.mainWindow, 'Title Database Missing',
                                            'The Title Database (wiitdb.txt) is missing. Do you want to download it?')
    if msgbox == QtWidgets.QMessageBox.Yes:
        return DownloadTitles()
    return False


def DownloadTitles():
    try:
        with urllib.request.urlopen('https://www.gametdb.com/wiitdb.txt?LANG=EN') as src, open(globalstuff.wiitdb, 'wb') as dst:
            dst.write(src.read())
        return True
    except:
        msgbox = QtWidgets.QMessageBox.question(globalstuff.mainWindow, 'Download Error',
                                                'There was an error during the database download. Retry?')
        if msgbox == QtWidgets.QMessageBox.Yes:
            DownloadTitles()
        else:
            return False


def TitleLookup(gid: str):
    """
    Looks up the game name for the given game id in the title database txt
    """
    # First, check the file is still here
    if os.path.exists(globalstuff.wiitdb):
        with open(globalstuff.wiitdb, 'rb') as f:
            next(f)  # Skip first line
            while True:
                try:  # Read the line, split it and check the game id. If it matches, return the game name
                    line = next(f).decode('utf-8', 'ignore').split(' = ')
                    if line[0].lower() == gid.lower():
                        return line[1].rstrip('\r\n')
                except StopIteration:  # We've reached EOF
                    return 'Unknown Game'
    else:
        # Ask the user if they want to download the database
        retry = DownloadError()
        if retry:
            TitleLookup(gid)  # Try again
        else:
            return 'Unknown Game'  # Gave up, RIP

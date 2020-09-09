"""
A tiny settings widget
"""
import configparser
import os

from PyQt5 import QtWidgets
from PyQt5.QtGui import QPalette, QColor
from PyQt5.Qt import Qt

import globalstuff


class SettingsWidget(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

        # Disable the "?" button and resizing
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setFixedSize(self.minimumSize())

        # Initialize some variables
        themelist = ['Default', 'Dark']

        # Autosave checkbox
        self.NoWarnLabel = QtWidgets.QLabel('Disable Close Warning')
        self.NoWarnCheckbox = QtWidgets.QCheckBox()
        self.NoWarnCheckbox.setChecked(globalstuff.nowarn)
        self.NoWarnCheckbox.stateChanged.connect(self.HandleNoWarn)

        # Theme selector
        self.ThemeLabel = QtWidgets.QLabel('Theme')
        self.Theme = QtWidgets.QComboBox()
        self.Theme.addItems(themelist)
        for index, content in enumerate(themelist):
            if content.lower() == globalstuff.theme:
                self.Theme.setCurrentIndex(index)
                break
        self.Theme.currentIndexChanged.connect(self.HandleThemeChoose)

        # Add elements to layout
        L = QtWidgets.QGridLayout()
        L.addWidget(self.NoWarnLabel, 0, 0)
        L.addWidget(self.NoWarnCheckbox, 0, 1)
        L.addWidget(self.ThemeLabel, 1, 0)
        L.addWidget(self.Theme, 1, 1)
        self.setLayout(L)
        self.setWindowTitle('Settings')

    def HandleNoWarn(self, state: int):
        globalstuff.nowarn = bool(state)

    def HandleThemeChoose(self, index: int):
        globalstuff.theme = self.Theme.itemText(index).lower()
        if globalstuff.theme == 'dark':
            globalstuff.app.setPalette(DarkPalette())
        else:
            globalstuff.app.setPalette(DefaultPalette())


def readconfig(config: configparser.ConfigParser, file='config.ini'):
    """
    Reads a config file, or creates one if it doesn't exist
    """
    if not os.path.isfile(file):
        config['General'] = {'NoWarning': 'False', 'Theme': 'default'}
    else:
        config.read(file)

    # Set the globals
    globalstuff.nowarn = config.getboolean('General', 'NoWarning')
    globalstuff.theme = config['General']['Theme']


def writeconfig(config: configparser.ConfigParser, file='config.ini'):
    """
    Writes settings to an ini file.
    """
    config.set('General', 'NoWarning', str(globalstuff.nowarn))
    config.set('General', 'Theme', globalstuff.theme)
    with open(file, 'w') as file:
        config.write(file)


def DarkPalette():
    """
    Does all the changes required for dark mode.
    """

    # Set style to fusion
    globalstuff.app.setStyle('Fusion')

    QSS = """
    QMdiSubWindow:title { background: #000000 }
    """

    # Set mdi area bg and stylesheet
    globalstuff.app.setStyleSheet(QSS)
    globalstuff.mainWindow.mdi.setBackground(Qt.darkGray)

    # Generate the palette
    darkpal = QPalette()
    darkpal.setColor(QPalette.Window, QColor(53, 53, 53))
    darkpal.setColor(QPalette.WindowText, Qt.white)
    darkpal.setColor(QPalette.Base, QColor(25, 25, 25))
    darkpal.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    darkpal.setColor(QPalette.ToolTipBase, Qt.white)
    darkpal.setColor(QPalette.ToolTipText, Qt.white)
    darkpal.setColor(QPalette.Text, Qt.white)
    darkpal.setColor(QPalette.Button, QColor(53, 53, 53))
    darkpal.setColor(QPalette.ButtonText, Qt.white)
    darkpal.setColor(QPalette.BrightText, Qt.red)
    darkpal.setColor(QPalette.Link, QColor(42, 130, 218))
    darkpal.setColor(QPalette.Highlight, QColor(42, 130, 218))
    darkpal.setColor(QPalette.HighlightedText, Qt.black)
    return darkpal


def DefaultPalette():
    """
    Resets the default palette.
    """

    # Set style to the first element of keys, which should be OS-specific
    globalstuff.app.setStyle(QtWidgets.QStyleFactory.keys()[0])

    # Reset mdi area bg and remove the stylesheet
    globalstuff.app.setStyleSheet('')
    globalstuff.mainWindow.mdi.setBackground(Qt.gray)

    # Return palette
    return globalstuff.app.style().standardPalette()

"""
A tiny settings widget
"""
import configparser
import os

from PyQt5 import QtWidgets
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

        if globalstuff.theme == 'dark':
            self.setStyleSheet(globalstuff.checkqss)

    def HandleNoWarn(self, state: int):
        globalstuff.nowarn = bool(state)

    def HandleThemeChoose(self, index: int):
        globalstuff.theme = self.Theme.itemText(index).lower()
        if globalstuff.theme == 'dark':
            SetDarkPalette()
            self.setStyleSheet(globalstuff.checkqss)
        else:
            SetLightPalette()
            self.setStyleSheet('')


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


def SetDarkPalette():
    """
    Does all the changes required for dark mode.
    """
    # Set style to fusion
    globalstuff.app.setStyle('Fusion')

    # Set mdi area bg
    globalstuff.mainWindow.mdi.setBackground(Qt.darkGray)

    # Set palette
    globalstuff.app.setPalette(globalstuff.darkpal)
    for window in globalstuff.mainWindow.mdi.subWindowList():
        window.widget().setPalette(globalstuff.textpal)
        if hasattr(window.widget(), 'TreeWidget'):
            window.widget().TreeWidget.setStyleSheet(globalstuff.treeqss)

    # Force stylesheet on menu bar because it doesn't want to cooperate
    qss = """
    QMenu::item { color: white }
    QMenu::item:disabled { color: transparent }
    """
    globalstuff.mainWindow.menuBar().setStyleSheet(qss)


def SetLightPalette():
    """
    Resets the default palette.
    """
    # Set style to the first element of keys, which should be OS-specific
    globalstuff.app.setStyle(QtWidgets.QStyleFactory.keys()[0])

    # Reset mdi area bg
    globalstuff.mainWindow.mdi.setBackground(Qt.gray)

    # Reset palette
    globalstuff.app.setPalette(globalstuff.app.style().standardPalette())
    for window in globalstuff.mainWindow.mdi.subWindowList():
        window.widget().setPalette(globalstuff.app.style().standardPalette())
        if hasattr(window.widget(), 'TreeWidget'):
            window.widget().TreeWidget.setStyleSheet('')

    # Reset menu bar stylesheet
    globalstuff.mainWindow.menuBar().setStyleSheet('')

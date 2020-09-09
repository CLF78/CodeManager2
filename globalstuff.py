"""
Fuck globals, all my homies hate globals
"""
from PyQt5.QtGui import QPalette, QColor
from PyQt5.Qt import Qt

# Main window
app = None
mainWindow = None

# Wii Title Database
wiitdb = 'wiitdb.txt'

# GCT specific data
gctmagic = b'\0\xd0\xc0\xde' * 2
gctend = b'\xf0' + b'\0' * 7

# Program settings
nowarn = False
theme = 'default'

# Palettes
# This palette is a workaround so that QMdiSubWindow titles don't look like crap
textpal = QPalette()
textpal.setColor(QPalette.Text, Qt.white)

# The actual dark mode palette
darkpal = QPalette()
darkpal.setColor(QPalette.Window, QColor(53, 53, 53))
darkpal.setColor(QPalette.WindowText, Qt.white)
darkpal.setColor(QPalette.Base, QColor(25, 25, 25))
darkpal.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
darkpal.setColor(QPalette.ToolTipBase, Qt.white)
darkpal.setColor(QPalette.ToolTipText, Qt.white)
darkpal.setColor(QPalette.Button, QColor(53, 53, 53))
darkpal.setColor(QPalette.ButtonText, Qt.white)
darkpal.setColor(QPalette.BrightText, Qt.red)
darkpal.setColor(QPalette.Link, QColor(42, 130, 218))
darkpal.setColor(QPalette.Highlight, QColor(42, 130, 218))
darkpal.setColor(QPalette.HighlightedText, Qt.black)

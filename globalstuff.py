"""
Fuck globals, all my homies hate globals
"""

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

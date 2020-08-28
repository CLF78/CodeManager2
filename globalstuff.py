"""
Fuck globals, all my homies hate globals
"""

mainWindow = None
wiitdb = 'wiitdb.txt'
gctmagic = b'\0\xd0\xc0\xde' * 2
gctend = b'\xf0' + b'\0' * 7

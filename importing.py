"""
This file contains multiple functions to import codelists.
"""
import re

from chardet import detect
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from widgets import ModdedSubWindow, ModdedTreeWidgetItem


def CreateCodelist(filename):
    win = ModdedSubWindow()
    win.setWidget(CodeList(filename))
    win.setAttribute(Qt.WA_DeleteOnClose)
    globalstuff.mainWindow.mdi.addSubWindow(win)
    win.show()
    return win.widget()


def ImportTXT(filename, codelist):
    """
    Imports a TXT. This took longer than it should have.
    """
    # Initialize vars
    gidrule = re.compile('^[\w]{4,6}$')
    linerule = re.compile('^(\* )?[\w]{8} [\w]{8}', re.IGNORECASE)
    parent = None
    unkcount = 0  # Used for codes without names

    # If the codelist param is not set, we want to create a new window, so do that
    if not codelist:
        codelist = CreateCodelist(filename)

    # Set the tree and lineedit widgets
    gidinput = codelist.gidInput
    codelist = codelist.Codelist

    # Open the file
    with open(filename, 'rb') as f:

        # Read the file, detect its encoding and split it into groups (there's an empty line between each entry)
        rawdata = f.read()
        rawdata = rawdata.decode(encoding=detect(rawdata)['encoding'], errors='ignore').split('\r\n' * 2)

        # Begin parsing groups
        for i, group in enumerate(rawdata):
            if not i:  # The first group contains the gameid, so check it with regex and set it if it's valid
                gameid = group.splitlines()[0]
                if gidinput.text() == 'UNKW00' and re.match(gidrule, gameid):  # Ignore it if the gameid is already set
                    gidinput.setText(gameid)
            else:
                # Initialize vars
                lines = group.splitlines()
                name = code = comment = ''
                isenabled = False

                # Parse the group and match each line with the code line regex
                for line in lines:
                    m = re.match(linerule, line)

                    # It's a code line
                    if m:
                        if '*' in m[0]:  # Asterisks are used to mark enabled codes, so mark it as such
                            isenabled = True
                        code = '\n'.join([code, m[0].replace('* ', '')])

                    # It's not a code line
                    else:
                        if name:  # We already have a name set, so add this line to the comment
                            comment = '\n'.join([comment, line])
                        else:  # The code doesn't have a name yet, so set it to this line
                            name = line

                # Failsafe if the code has no name
                if not name:
                    name = 'Unknown Code'
                    if unkcount != 1:
                        name += str(unkcount)
                    unkcount += 1

                # Create the tree entry
                newitem = ModdedTreeWidgetItem(name, False, True)

                # Set the check accordingly
                if isenabled:
                    newitem.setCheckState(0, Qt.Checked)

                # Determine parenthood
                if parent and code:
                    parent.addChild(newitem)  # Only nest codes, not categories, TXTs don't let you do this.
                else:
                    codelist.addTopLevelItem(newitem)

                # Finally, insert the data. What a wild ride.
                if code:
                    newitem.setText(1, code[1:].upper())  # Force uppercase, because lowercase sucks.
                    newitem.setText(2, comment[1:])  # Btw, the first character is a newline, so i'm removing it.
                else:
                    newitem.setAsCategory(True)
                    parent = newitem

"""
This file contains multiple functions to import codelists.
"""
import os
import re

from chardet import detect
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from widgets import ModdedSubWindow, ModdedTreeWidgetItem


def DoPreliminaryOperations(filename, codelist):
    """
    This function performs a couple preliminary operations before importing can take place. Very informative, i know.
    """
    # Check if we can read the file. If not, trigger an error message.
    if not os.access(filename, os.R_OK):
        QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'File Read Error', "Couldn't read file " + filename, QtWidgets.QMessageBox.Ok).exec_()
        return None

    # If the codelist param is not set, we want to create a new window, so do that
    if not codelist:
        win = ModdedSubWindow()
        win.setWidget(CodeList(filename))
        win.setAttribute(Qt.WA_DeleteOnClose)
        globalstuff.mainWindow.mdi.addSubWindow(win)
        win.show()
        return win
    return codelist


def ImportTXT(filename, codelist):
    """
    Imports a TXT. This took longer than it should have.
    """
    # Initialize vars
    gidrule = re.compile('^[\w]{4,6}$')
    linerule = re.compile('^(\* )?[\w]{8} [\w]{8}', re.IGNORECASE)
    parent = None
    unkcount = 1  # Used for codes without names

    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        codelist.close()
        return

    # Set the tree and lineedit widgets
    gidinput = codelist.widget().gidInput
    codelist = codelist.widget().Codelist

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
                    if unkcount > 1:
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


def ImportINI(filename, codelist):
    """
    ImportTXT's uglier brother. Also, Dolphin is an asshole.
    """
    # Initialize vars
    gidrule = re.compile('^[\w]{4,6}$')

    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Set the tree and lineedit widgets
    gidinput = codelist.widget().gidInput
    codelist = codelist.widget().Codelist

    # Set the gameID
    gameid = os.path.splitext(os.path.basename(filename))[0]  # Remove the file extension
    if re.match(gidrule, gameid):
        gidinput.setText(gameid)

    # Open the file
    with open(filename) as f:
        rawdata = f.read().splitlines()
        length = len(rawdata)

        # First, we have to find the sections containing the codes between all the file's sections
        n = o = 0
        m = p = length  # These will be set to the end of the file, in case there are no other sections than what we need
        for i, line in enumerate(rawdata, 1):  # This starts from 1, in case of the first section being at index 0
            if line == '[Gecko]':
                n = i
            elif line == '[Gecko_Enabled]':
                o = i
            elif i < length - 1 and rawdata[i].startswith('['):
                """
                If the next line begins a section, set this line as the end of the current section, but with some limits:
                - If n > o, we're in the Gecko section. But if m is set, we're somewhere between them, so don't do anything
                - If o < n, we're in the Gecko_Enabled section. But if p is set, we're somewhere between them, so don't do anything
                - Finally, if o = n, it means we're in an unknown section, so don't do anything either.
                """
                if n > o and m == length:
                    m = i
                elif n < o and p == length:
                    p = i

        # We got the indexes, create the subsections. My palms are already sweating.
        gecko = rawdata[n:m]
        geckoenabled = rawdata[o:p]

        # Initialize vars
        entrylist = []
        unkcount = 1

        # Parse the gecko section
        for line in gecko:
            if line.startswith('$'):  # It's a code name, and code names need some extra parsing
                # First, we must exclude the author from the code name, as it will fuck up Gecko_Enabled otherwise
                charcount = 1
                for char in line[1:]:
                    if char == '[':
                        charcount -= 1  # Subtracting one because there's a space before this character
                        break
                    charcount += 1

                # if the resulting name is empty, apply the following failsafe
                if charcount == 1:
                    line += 'Unknown Code'
                    if unkcount > 1:
                        line += str(unkcount)

                # Create the widget
                newitem = ModdedTreeWidgetItem(line[1:charcount], False, True)
                entrylist.append(newitem)
            elif line.startswith('*'):  # It's a comment line
                if len(line) > 1:
                    newitem.setText(2, '\n'.join([newitem.text(2), line[1:]]))  # Only add if the line is not empty
            else:  # It's a code line
                newitem.setText(1, '\n'.join([newitem.text(1), line.upper()]))

        # Parse the geckoenabled section. I can see the light at the end of the tunnel.
        for item in entrylist:
            if '$' + item.text(0) in geckoenabled:
                item.setCheckState(0, Qt.Checked)  # Enable the check if the name matches
            item.setText(1, item.text(1)[1:])  # Also remove the extra newlines at the beginning of these two fields
            item.setText(2, item.text(2)[1:])

        # Finally, add all the newly created widgets to the codelist. Insert obligatory "Fuck Dolphin" here.
        codelist.addTopLevelItems(entrylist)

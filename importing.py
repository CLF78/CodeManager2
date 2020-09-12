"""
This file contains multiple functions to import codelists.
"""
import os
import re
from itertools import chain
from typing import Optional, BinaryIO

from chardet import detect
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from common import GameIDMismatch, AssembleCode
from codelist import CodeList
from widgets import ModdedSubWindow, ModdedTreeWidgetItem


def GameIDCheck(gameid: str, codelist: CodeList):
    """
    Checks if the game id matches the codelist's current one. If not, it alerts the user, asking them whether they
    want to continue importing or not.
    """
    if codelist.gameID != gameid:
        if codelist.gameID != 'UNKW00' and GameIDMismatch() == QtWidgets.QMessageBox.No:
            return False
        codelist.SetGameID(gameid.upper())
    return True


def DoPreliminaryOperations(filename: str, codelist: Optional[CodeList]):
    """
    This function performs a couple preliminary operations before importing can take place. Very informative, i know.
    """
    # Check if we can read the file. If not, trigger an error message.
    if not os.access(filename, os.R_OK):
        QtWidgets.QMessageBox.critical(globalstuff.mainWindow, 'File Read Error', "Couldn't read file " + filename)
        return None

    # If the codelist param is not set, we want to create a new window, so do that
    if not codelist:
        return globalstuff.mainWindow.CreateNewWindow(CodeList(''))
    return codelist


def ImportTXT(filename: str, codelist: CodeList):
    """
    Imports a TXT. This took longer than it should have.
    """
    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Initialize vars
    linerule = re.compile('^(\* )?[\w]{8} [\w]{8}$', re.I)
    unkcount = 1  # Used for codes without names
    currdepth = 0  # Current depth, used for sub-categories
    parents = {'0': None}  # This dict stores the parent for each level. Not the best solution, but it gets the job done.

    # Set the tree widget
    listwidget = codelist.TreeWidget

    # Open the file and read it
    with open(filename, 'rb') as f:
        rawdata = f.read()

    # Now that we read the file, detect its encoding and split it into groups (there's an empty line between each).
    # This is done because the original Code Manager saves in UTF-16, which would fuck up the formatting if not decoded.
    rawdata = rawdata.decode(detect(rawdata)['encoding'], 'ignore').split(os.linesep * 2)

    # The first group contains the gameid, so check it with regex and set it if it's valid
    gameid = rawdata[0].splitlines()[0].strip()
    if 4 <= len(gameid) <= 6:
        if not GameIDCheck(gameid, codelist):
            return
    rawdata.pop(0)  # Remove the parsed group

    # Begin parsing codes
    for group in rawdata:

        # Initialize vars
        name = code = comment = author = ''
        isenabled = False

        # Parse group
        for line in group.splitlines():
            m = re.match(linerule, line)

            # It's a code line
            if m:
                if not isenabled and '*' in m[0]:  # Asterisks are used to mark enabled codes, so mark it as such
                    isenabled = True
                code = '\n'.join([code, m[0].lstrip('* ')])

            # It's not a code line
            else:
                if name:  # We already have a name set, so add this line to the comment
                    comment = '\n'.join([comment, line])
                else:  # The code doesn't have a name yet, so set it to this line. Also check for the author name
                    lspl = line.split(' [')
                    name = lspl[0]
                    if len(lspl) > 1:
                        author = lspl[1].rstrip(']')  # Remove the last character

        # Failsafe if the code name is fully empty
        if not name:
            name = 'Unknown Code '
            while listwidget.findItems(name + str(unkcount), Qt.MatchExactly):
                unkcount += 1
            name += str(unkcount)

        # If the name only contains "#" characters, it represents the end of a category, so don't add it to the tree
        if not name.lstrip('#'):
            currdepth = name.count('#') - 1

        # Else, create the tree item
        else:
            newitem = ModdedTreeWidgetItem(name.lstrip('#'), not(bool(code)), True)

            # If it's a category, set the depth and the parents key
            if not code:
                currdepth = name.count('#')
                parents[str(currdepth+1)] = newitem

            # Otherwise, it's a code, so add the code, comment and author
            else:
                newitem.setText(1, code.lstrip('\n').upper())  # Force uppercase, because lowercase sucks.
                newitem.setText(2, comment.lstrip('\n'))
                newitem.setText(4, author)

                # If enabled, tick the check
                if isenabled:
                    newitem.setCheckState(0, Qt.Checked)

                # If the name is unknown, look it up
                if 'Unknown Code' in newitem.text(0):
                    globalstuff.mainWindow.CodeLookup(newitem, codelist, gameid)

            # Set the item's parent. If there's a key error, don't do anything. Gotta stay safe.
            try:
                parent = parents[str(currdepth)]
            except KeyError:
                pass

            # Determine parenthood. Don't believe the warning! Currdepth is 0 even if all parent changes are skipped ;)
            if parent:
                parent.addChild(newitem)
            else:
                listwidget.addTopLevelItem(newitem)

            # Add 1 to depth, as children will be 1 level further down
            if not code:
                currdepth += 1

    # Finally, trigger the buttons in the codelist
    codelist.EnableButtons()
    codelist.UpdateLines()


def ImportINI(filename: str, codelist: CodeList):
    """
    ImportTXT's uglier brother. Also, Dolphin is an asshole.
    """
    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Set the tree widget
    listwidget = codelist.TreeWidget

    # Set the gameID
    gameid = os.path.splitext(os.path.basename(filename))[0]  # Remove the file extension
    if 4 <= len(gameid) <= 6 and not GameIDCheck(gameid, codelist):
        return

    # Open the file
    with open(filename) as f:
        rawdata = f.read().splitlines()

    # First, we have to find the sections containing the codes between all the file's sections
    length = len(rawdata)
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
            - If n < o, we're in the Gecko_Enabled section. But if p is set, we're somewhere between them, so don't do anything
            - Finally, if n = o, it means we're in an unknown section, so don't do anything either.
            """
            if n > o and m == length:
                m = i
            elif n < o and p == length:
                p = i

    # We got the indexes, create the subsections. My palms are already sweating.
    gecko = rawdata[n:m]
    geckoenabled = rawdata[o:p]

    # The rest of the file won't be wasted! It will be stored so if the user exports the list as ini, this data will be
    # ported over.
    if n or p != length or m != o-1:
        scrap = '\n'.join(chain(rawdata[:n-1], rawdata[m:o-1], rawdata[p:]))
        if scrap:
            codelist.scrap = scrap

    # Initialize vars
    entrylist = []
    unkcount = 1

    # Parse the gecko section
    for line in gecko:

        # It's a code name, and code names need some extra parsing
        if line.startswith('$'):

            # First, we must exclude the author from the code name, as it will fuck up Gecko_Enabled otherwise
            lspl = line.split(' [')
            name = lspl[0].lstrip('$')  # Remove the first character

            # Set the author name if present
            author = ''
            if len(lspl) > 1:
                author = lspl[1].rstrip(']')  # Remove the last character

            # If the resulting name is empty, apply the following failsafe
            if not name:
                name = 'Unknown Code '
                while listwidget.findItems(name + str(unkcount), Qt.MatchExactly):
                    unkcount += 1
                name += str(unkcount)
                unkcount += 1

            # Create the widget
            newitem = ModdedTreeWidgetItem(name, False, True)
            newitem.setText(4, author)
            entrylist.append(newitem)

        # It's a comment line. Not using "and" because the line would end up in the "else"
        elif line.startswith('*'):
            if len(line) > 1:
                newitem.setText(2, '\n'.join([newitem.text(2), line.lstrip('*')]))  # Only add if the line is not empty

        # It's a code line
        else:
            newitem.setText(1, '\n'.join([newitem.text(1), line.upper()]))

    # Parse the geckoenabled section and add the newly created widgets to the codelist
    for item in entrylist:

        # Enable the check if the name matches
        if '$' + item.text(0) in geckoenabled:
            item.setCheckState(0, Qt.Checked)

        # Remove the extra newlines at the beginning of these two fields
        item.setText(1, item.text(1).lstrip('\n'))
        item.setText(2, item.text(2).lstrip('\n'))

        # Do code lookup if code doesn't have a name
        if 'Unknown Code' in item.text(0):
            globalstuff.mainWindow.CodeLookup(item, codelist, gameid)

        # Add to tree widget
        listwidget.addTopLevelItem(item)

    # Finally, trigger the buttons in the codelist
    codelist.EnableButtons()
    codelist.UpdateLines()


def ImportGCT(filename: str, codelist: CodeList):
    """
    ImportTXT's siamese twins.
    """
    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Do the parsing
    with open(filename, 'rb') as f:
        if f.read(8) == globalstuff.gctmagic:  # Check for the magic
            f.seek(-8, 2)  # Go to the end of the file

            # If the "Codelist End" is at the end of the file, we have a regular GCT
            if f.read() == globalstuff.gctend:
                ParseGCT(os.path.splitext(os.path.basename(filename))[0], f, codelist)

            # Otherwise we have an extended GCT
            else:
                ParseExtendedGCT(f, codelist)
        else:
            # This ain't it, chief
            QtWidgets.QMessageBox.critical(globalstuff.mainWindow, 'Invalid file', 'This file is invalid')


def ParseExtendedGCT(f: BinaryIO, codelist: CodeList):
    """
    BrawlBox allows you to store code names and offsets in the GCT. So, this is for GCTs using that feature.
    """
    # Initialize vars
    backupoffset = 0

    # Set the tree widget
    listwidget = codelist.TreeWidget

    # First, let's get the file's length
    filelen = f.tell()
    f.seek(0)

    # Now, let's find the codelist end
    while f.tell() < filelen:
        if f.read(8) == globalstuff.gctend:
            f.seek(4, 1)
            backupoffset = f.tell()  # Saving this for when i need to go back
            break

    # Failsafe time
    if f.tell() == filelen:
        QtWidgets.QMessageBox.critical(globalstuff.mainWindow, 'Invalid file', 'This file is invalid')
        return

    # Now let's find the game id. Why -8 ?
    # First, the offset is according to the entry's beginning (aka the game name which was skipped)
    # Second, the seek needs to be re-adjusted due to the read operation
    f.seek(int.from_bytes(f.read(4), 'big')-8, 1)

    # Get the string
    gameid = ''
    while f.tell() < filelen:
        char = f.read(1)
        if char == b'\0':
            break
        gameid += char.decode('utf-8', 'ignore')

    # Verify the gameid's validity
    if 4 <= len(gameid) <= 6 and not GameIDCheck(gameid, codelist):
        return

    # Read the amount of codes
    f.seek(backupoffset)  # Go back
    f.seek(4, 1)
    amount = int.from_bytes(f.read(4), 'big')

    # Begin reading codes!
    while amount > 0:
        # Read the offsets
        codeoffs = int.from_bytes(f.read(4), 'big')
        codelen = int.from_bytes(f.read(4), 'big')
        nameoffs = f.tell() + int.from_bytes(f.read(4), 'big') - 8  # Offset starts at beginning of entry
        commentoffs = f.tell() + int.from_bytes(f.read(4), 'big') - 12  # Same here
        if commentoffs < f.tell():  # If there's no comment the value is 0, so if we subtract 12 we'll be at a smaller offset
            commentoffs = 0
        backupoffset = f.tell()

        # Go to the code and read it
        f.seek(codeoffs)
        code = AssembleCode(f.read(codelen * 8).hex())  # Convert to hex string and add spaces and newlines

        # Go to the code name and read it
        codename = ''
        f.seek(nameoffs)
        while f.tell() < filelen:
            char = f.read(1)
            if char == b'\0':
                break
            codename += char.decode('utf-8', 'ignore')

        # Find the author inside the name
        lspl = codename.split(' [')
        codename = lspl[0]
        author = ''
        if len(lspl) > 1:
            author = lspl[1].rstrip(']')  # Remove the last character

        # Go the comment and read it
        comment = ''
        if commentoffs:
            f.seek(commentoffs)
            while f.tell() < filelen:
                char = f.read(1)
                if char == b'\0':
                    break
                comment += char.decode('utf-8', 'ignore')

        # Create the tree widget
        newitem = ModdedTreeWidgetItem(codename, False, True)
        newitem.setText(1, code)
        newitem.setText(2, comment)
        newitem.setText(4, author)
        listwidget.addTopLevelItem(newitem)

        # Go back to the offset we backed up earlier
        f.seek(backupoffset)
        amount -= 1


def ParseGCT(filename: str, f: BinaryIO, codelist: CodeList):
    """
    This GCT parser is for the normal format. It tries to split codes according to the codetypes.
    """
    # Initialize vars
    currentcode = False
    amount = 0
    unkcount = 1
    finalist = []

    # Set the tree widget
    listwidget = codelist.TreeWidget

    # First, let's get the file's length
    filelen = f.tell() - 8  # Ignore the F0 line
    f.seek(8)  # Go back to the beginning and skip the GCT magic

    # Verify the gameid's validity
    gameid = os.path.splitext(os.path.basename(filename))[0]
    if 4 <= len(gameid) <= 6 and not GameIDCheck(gameid, codelist):
        return

    # Begin reading the GCT!
    while f.tell() < filelen:
        # Read the next line and get its first byte
        line = f.read(8)
        c = int(hex(line[0]), 16)

        # If we are currently in a code
        if currentcode:
            # If we have exhausted the amount of lines specified or we meet an "E0" line, don't add anymore lines
            if amount == 0 or (amount == -1 and c == 0xE0):
                currentcode = False
            elif amount > 0:
                amount -= 1

            # Add the line. Yes PyCharm, i know newitem could be referenced before assignment, but currentcode is never
            # true when the loop begins, so shut the fuck up.
            newitem.setText(1, newitem.text(1) + line.hex())

        # It's a new code!
        else:
            # Set name
            name = 'Unknown Code '
            while listwidget.findItems(name + str(unkcount), Qt.MatchExactly):
                unkcount += 1
            name += str(unkcount)
            unkcount += 1

            # Create the tree widget item
            newitem = ModdedTreeWidgetItem(name, False, True)
            newitem.setText(1, line.hex())
            finalist.append(newitem)

            # Check the codetype. If the line isn't listed here, it will be added as a single line if found standalone.
            # Type 06 (length specified by code, in bytes)
            if c == 6 or c == 7:
                lines = int(line[7:].hex(), 16)
                amount = (lines + 7) // 8 - 1  # Add 7 to approximate up
                currentcode = True

            # Type 08 (fixed length)
            elif c == 8 or c == 9:
                currentcode = True

            # Type 20-2F, 40, 42, 48, 4A, A8-AE, F6 (add lines until we find an E0 line)
            elif 0x20 <= c <= 0x2F or c == 0x40 or c == 0x42 or c == 0x48 or c == 0x4A or 0xA8 <= c <= 0xAE or c == 0xF6:
                amount = -1
                currentcode = True

            # Type C0, C2, C4, F2/F4 (length specified by code, in lines)
            elif c == 0xC0 or 0xC2 <= c <= 0xC5 or 0xF2 <= c <= 0xF5:
                amount = int(line[7:].hex(), 16) - 1
                currentcode = True

    # Add spaces and newlines to the codes, then add the items to the tree
    for item in finalist:
        item.setText(1, AssembleCode(item.text(1)))
        globalstuff.mainWindow.CodeLookup(item, listwidget, filename)
        listwidget.addTopLevelItem(item)


def ImportDOL(filename: str, codelist: CodeList):
    """
    The ImportGCT twins' older sister.
    """
    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Initialize vars
    sections = []

    # Do the parsing
    with open(filename, 'rb') as f:
        # Get the entrypoint
        f.seek(0xE0)
        entrypoint = int(f.read(4).hex(), 16)

        # Go to the text sections' loading address. The one with the same address as the entrypoint usually contains the
        # codehandler+gct. But other custom code might override this, so as an additional check for 0x80001800 is made
        f.seek(0x48)
        for i in range(7):
            secmem = int(f.read(4).hex(), 16)
            if secmem == entrypoint or secmem == 0x80001800:
                sections.append(i)

        # If there are no matches, it means there's no codes here for us to find
        if not sections:
            QtWidgets.QMessageBox.critical(globalstuff.mainWindow, 'Empty DOL', 'No GCTs were found in this file')
            return

        for section in sections:
            # Get the section offset and length
            f.seek(section * 4)
            sectionoffset = int(f.read(4).hex(), 16)
            f.seek(0x90 + section * 4)
            sectionend = sectionoffset + int(f.read(4).hex(), 16)

            # Initialize vars
            shouldadd = False
            buffer = globalstuff.gctmagic

            # Read the section
            f.seek(sectionoffset)
            while f.tell() < sectionend:
                # Read file
                bytez = f.read(8)

                # Check for the gct EOF, else add to the buffer if we found the magic
                if shouldadd:
                    buffer += bytez
                    if bytez == globalstuff.gctend:
                        break

                # Found the GCT magic, start reading from here
                elif bytez == globalstuff.gctmagic:
                    shouldadd = True

            # Skip the parsing if we didn't find anything
            if len(buffer) == 8:
                continue

            # Write the buffer to a temporary file, then feed it to the GCT parser
            with open('tmp.gct', 'wb+') as g:
                g.write(buffer)
                ParseGCT('tmp.gct', g, codelist)

            # Remove the file
            os.remove('tmp.gct')
            return  # We're assuming there is only one GCT here. Who in their right mind would add more than one?!

    # This is only shown if nothing is found, as otherwise the function would have already returned
    QtWidgets.QMessageBox.critical(globalstuff.mainWindow, 'Empty DOL', 'No GCTs were found in this file')

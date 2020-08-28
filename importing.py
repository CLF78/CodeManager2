"""
This file contains multiple functions to import codelists.
"""
import os
import re

from chardet import detect
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from common import GameIDMismatch
from codelist import CodeList
from widgets import ModdedSubWindow, ModdedTreeWidgetItem


def GameIDCheck(gameid, codelist):
    """
    Checks if the game id matches the codelist's current one. If not, it alerts the user, asking them whether they
    want to continue importing or not.
    """
    if codelist.gameID != gameid:
        if codelist.gameID != 'UNKW00':
            ret = GameIDMismatch()  # Raise awareness!
            if ret == QtWidgets.QMessageBox.No:
                return False
        codelist.SetGameID(gameid)
    return True


def DoPreliminaryOperations(filename, codelist):
    """
    This function performs a couple preliminary operations before importing can take place. Very informative, i know.
    """
    # Check if we can read the file. If not, trigger an error message.
    if not os.access(filename, os.R_OK):
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle('File Read Error')
        msgbox.setText("Couldn't read file " + filename)
        msgbox.exec_()
        return None

    # If the codelist param is not set, we want to create a new window, so do that
    if not codelist:
        win = ModdedSubWindow()
        win.setWidget(CodeList(''))
        win.setAttribute(Qt.WA_DeleteOnClose)
        globalstuff.mainWindow.mdi.addSubWindow(win)
        win.show()
        return win.widget()
    return codelist


def ImportTXT(filename, codelist):
    """
    Imports a TXT. This took longer than it should have.
    """
    # Initialize vars
    linerule = re.compile('^(\* )?[\w]{8} [\w]{8}', re.IGNORECASE)
    unkcount = 1  # Used for codes without names
    currdepth = 0  # Current depth, used for sub-categories
    parents = {'0': None}  # This dict stores the parent for each level. Not the best solution, but it gets the job done.

    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Set the tree widget
    listwidget = codelist.Codelist

    # Open the file and read it
    with open(filename, 'rb') as f:
        rawdata = f.read()

    # Now that we read the file, detect its encoding and split it into groups (there's an empty line between each).
    # This is done because the original Code Manager saves in UTF-16, which would fuck up the formatting if not decoded.
    rawdata = rawdata.decode(detect(rawdata)['encoding'], 'ignore').split('\r\n' * 2)

    # The first group contains the gameid, so check it with regex and set it if it's valid
    gameid = rawdata[0].splitlines()[0]
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
                if '*' in m[0]:  # Asterisks are used to mark enabled codes, so mark it as such
                    isenabled = True
                code = '\n'.join([code, m[0].replace('* ', '')])

            # It's not a code line
            else:
                if name:  # We already have a name set, so add this line to the comment
                    comment = '\n'.join([comment, line])
                else:  # The code doesn't have a name yet, so set it to this line. Also check for the author name
                    lspl = line.split(' [')
                    name = lspl[0]
                    if len(lspl) > 1:
                        author = lspl[1][:-1]  # Remove the last character

        # Failsafe if the code name is fully empty
        if not name:
            name = 'Unknown Code '
            while listwidget.findItems(name + str(unkcount), Qt.MatchExactly):
                unkcount += 1
            name += str(unkcount)

        # If the name only contains "#" characters, it represents the end of a category, so don't add it to the tree
        if not name.replace('#', ''):
            currdepth = name.count('#') - 1
            continue

        # Else, create the tree item
        else:
            newitem = ModdedTreeWidgetItem(name.replace('#', ''), False, True)

            # If it's a category, set the depth and the other flags
            if not code:
                currdepth = name.count('#')
                parents[str(currdepth+1)] = newitem
                newitem.setAsCategory(True)

            # Otherwise, it's a code, so add the code, comment and author
            else:
                newitem.setText(1, code[1:].upper())  # Force uppercase, because lowercase sucks.
                newitem.setText(2, comment[1:])  # Btw, the first character is a newline, so i'm removing it.
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


def ImportINI(filename, codelist):
    """
    ImportTXT's prettier brother. Also, Dolphin is an asshole.
    """
    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Set the tree widget
    listwidget = codelist.Codelist

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
            lspl = line.split(' [')

            name = lspl[0][1:]  # Remove the first character
            author = ''
            if len(lspl) > 1:
                author = lspl[1][:-1]  # Remove the last character

            # If the resulting name is empty, apply the following failsafe
            if not len(name):
                line = 'Unknown Code '
                while listwidget.findItems(line + str(unkcount), Qt.MatchExactly):
                    unkcount += 1
                line += str(unkcount)

            # Create the widget
            newitem = ModdedTreeWidgetItem(name, False, True)
            newitem.setText(4, author)
            entrylist.append(newitem)
        elif line.startswith('*'):  # It's a comment line. Not using "and" because the line would end up in the "else"
            if len(line) > 1:
                newitem.setText(2, '\n'.join([newitem.text(2), line[1:]]))  # Only add if the line is not empty
        else:  # It's a code line
            newitem.setText(1, '\n'.join([newitem.text(1), line.upper()]))

    # Parse the geckoenabled section and add the newly created widgets to the codelist.
    for item in entrylist:

        # Enable the check if the name matches
        if '$' + item.text(0) in geckoenabled:
            item.setCheckState(0, Qt.Checked)

        # Remove the extra newlines at the beginning of these two fields
        item.setText(1, item.text(1)[1:])
        item.setText(2, item.text(2)[1:])

        # Do code lookup if code doesn't have a name
        if 'Unknown Code' in item.text(0):
            globalstuff.mainWindow.CodeLookup(item, codelist, gameid)

        # Add to tree widget
        listwidget.addTopLevelItem(item)


def ImportGCT(filename, codelist):
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
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Invalid file')
            msgbox.setText('This file is invalid')
            msgbox.exec_()


def ParseExtendedGCT(f, codelist):
    """
    BrawlBox allows you to store code names and offsets in the GCT. So, this is for GCTs using that feature.
    """
    # Initialize vars
    backupoffset = 0

    # Set the tree widget
    listwidget = codelist.Codelist

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
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle('Invalid file')
        msgbox.setText('This file is invalid')
        msgbox.exec_()
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
        if commentoffs < f.tell():  # If there's no comment, the value is 0, so if we subtract 12 we'll be at a smaller offset
            commentoffs = 0
        backupoffset = f.tell()

        # Go to the code and read it
        f.seek(codeoffs)
        code = f.read(codelen * 8).hex().upper()  # Convert to uppercase hex string

        # Split the code with space and newlines
        assembledcode = ''
        for index, char in enumerate(code):
            if not index % 16 and index:
                assembledcode = '\n'.join([assembledcode, char])
            elif not index % 8 and index:
                assembledcode = ' '.join([assembledcode, char])
            else:
                assembledcode = ''.join([assembledcode, char])

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
            author = lspl[1][:-1]  # Remove the last character

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
        newitem.setText(1, assembledcode)
        newitem.setText(2, comment)
        newitem.setText(4, author)
        listwidget.addTopLevelItem(newitem)

        # Go back to the offset we backed up earlier
        f.seek(backupoffset)
        amount -= 1


def ParseGCT(filename, f, codelist):
    """
    This GCT parser is for the normal format. It tries to split codes according to the codetypes.
    """
    # Initialize vars
    currentcode = False
    amount = 0
    unkcount = 1
    finalist = []

    # Set the tree widget
    listwidget = codelist.Codelist

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
            if amount == 0 or (amount == -1 and c == 224):
                currentcode = False
            else:
                amount -= 1

            # Add the line. Yes PyCharm, i know newitem could be referenced before assignment, but currentcode is never
            # true when the loop begins, so shut the fuck up.
            newitem.setText(1, newitem.text(1) + line.hex().upper())

        # It's a new code!
        else:
            # Create the tree widget item
            name = 'Unknown Code '
            while listwidget.findItems(name + str(unkcount), Qt.MatchExactly):
                unkcount += 1
            name += str(unkcount)
            newitem = ModdedTreeWidgetItem(name, False, True)
            newitem.setText(1, line.hex().upper())
            finalist.append(newitem)

            # Check the codetype. If the line isn't listed here, it will be added as a single line if found standalone.
            # Type 06 (length specified by code, in bytes)
            if c == 6 or c == 7:
                lines = int(line[7:].hex(), 16)
                if lines % 8:  # This is so that half-lines are counted properly
                    lines += 7
                amount = lines // 8 - 1
                currentcode = True

            # Type 08 (fixed length)
            elif c == 8 or c == 9:
                currentcode = True

            # Type 20-2F, 40, 42, 48, 4A, A8-AE, F6 (add lines until we find an E0 line)
            elif 32 <= c <= 47 or c == 68 or c == 70 or c == 72 or c == 74 or 168 <= c <= 174 or c == 246:
                amount = -1
                currentcode = True

            # Type C0/C2, F2 (length specified by code, in lines)
            elif c == 192 or c == 194 or c == 195 or c == 242:
                amount = int(line[7:].hex(), 16) - 1
                currentcode = True

    # Add spaces and newlines to the codes
    for item in finalist:
        assembledcode = ''
        for index, char in enumerate(item.text(1)):
            if not index % 16 and index:
                assembledcode = '\n'.join([assembledcode, char])
            elif not index % 8 and index:
                assembledcode = ' '.join([assembledcode, char])
            else:
                assembledcode = ''.join([assembledcode, char])
        item.setText(1, assembledcode)

    # Add the codes to the widget
    for item in finalist:
        globalstuff.mainWindow.CodeLookup(item, listwidget, filename)
        listwidget.addTopLevelItem(item)


def ImportDOL(filename, codelist):
    """
    The ImportGCT twins' older sister.
    """
    # Initialize vars
    sections = []

    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Do the parsing
    with open(filename, 'rb') as f:
        # Get the entrypoint
        f.seek(224)
        entrypoint = int(f.read(4).hex(), 16)

        # Go to the text sections' loading address. The one with the same address as the entrypoint usually contains the
        # codehandler+gct. But other custom code might override this, so as an additional check for 0x80001800 is made
        f.seek(72)
        for i in range(7):
            secmem = int(f.read(4).hex(), 16)
            if secmem == entrypoint or secmem == 0x80001800:
                sections.append(i)

        # If there are no matches, it means there's no codes here for us to find
        if not sections:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Empty DOL')
            msgbox.setText('No GCTs were found in this file')
            msgbox.exec_()
            return

        for section in sections:
            # Get the section offset and length
            f.seek(4 * section)
            sectionoffset = int(f.read(4).hex(), 16)
            f.seek(144 + section * 4)
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
                g.seek(0, 2)
                ParseGCT('tmp.gct', g, codelist)

            # Remove the file
            os.remove('tmp.gct')

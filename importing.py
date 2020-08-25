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
        return win.widget()
    return codelist


def ImportTXT(filename, codelist):
    """
    Imports a TXT. This took longer than it should have.
    """
    # Initialize vars
    gidrule = re.compile('^[\w]{4,6}$')
    linerule = re.compile('^(\* )?[\w]{8} [\w]{8}', re.IGNORECASE)
    parent = None
    unkcount = 0  # Used for codes without names

    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

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
                    name = 'Unknown Code '
                    unkcount += 1
                    while codelist.findItems(name + str(unkcount), Qt.MatchExactly):
                        unkcount += 1
                    name += str(unkcount)

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
    # Perform the initial operations. If they fail, abort everything.
    codelist = DoPreliminaryOperations(filename, codelist)
    if not codelist:
        return

    # Set the tree and lineedit widgets
    gidinput = codelist.gidInput
    codelist = codelist.Codelist

    # Set the gameID
    gameid = os.path.splitext(os.path.basename(filename))[0]  # Remove the file extension
    if 4 <= len(gameid) <= 6:
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
        unkcount = 0

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
                    line += 'Unknown Code '
                    unkcount += 1
                    while codelist.findItems(line + str(unkcount), Qt.MatchExactly):
                        unkcount += 1
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
        if f.read(8) == b'\0\xd0\xc0\xde' * 2:  # Check for the magic
            f.seek(-8, 2)  # Go to the end of the file

            # If the "Codelist End" is at the end of the file, we have a regular GCT
            if f.read() == b'\xf0' + b'\0' * 7:
                ParseGCT(os.path.splitext(os.path.basename(filename))[0], f, codelist)

            # Otherwise we have an extended GCT
            else:
                ParseExtendedGCT(f, codelist)
        else:
            # This ain't it, chief
            codelist.close()
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Invalid File', 'This file is not a GCT', QtWidgets.QMessageBox.Ok).exec_()


def ParseExtendedGCT(f, codelist):
    """
    BrawlBox allows you to store code names and offsets in the GCT. So, this is for GCTs using that feature.
    """
    # Initialize vars
    backupoffset = 0

    # Set the lineedit widget
    gidinput = codelist.gidInput
    listwidget = codelist.Codelist

    # First, let's get the file's length
    filelen = f.tell()
    f.seek(0)

    # Now, let's find the codelist end
    while f.tell() < filelen:
        if f.read(8) == b'\xf0' + b'\0' * 7:
            f.seek(4, 1)
            backupoffset = f.tell()  # Saving this for when i need to go back
            break

    # Failsafe time
    if f.tell() == filelen:
        codelist.close()
        QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Invalid File', 'This file is not a GCT', QtWidgets.QMessageBox.Ok).exec_()
        return

    # Now let's find the game id
    gameid = ''
    f.seek(int.from_bytes(f.read(4), 'big')-8, 1)  # Adjusting by 8 as the offset is according to the entry's beginning
    # (aka the game name which we skipped), and the seek needs to be re-adjusted due to the read operation

    # Get the string
    while f.tell() < filelen:
        char = f.read(1)
        if char == b'\0':
            break
        gameid += char.decode('utf-8')

    # Verify the gameid's validity
    if 4 <= len(gameid) <= 6:
        gidinput.setText(gameid)

    # Read the amount of codes
    f.seek(backupoffset)  # Go back
    f.seek(4, 1)
    amount = int.from_bytes(f.read(4), 'big')

    # Begin reading codes!
    while amount > 0:
        # Read the offsets
        codeoffs = int.from_bytes(f.read(4), 'big')
        codelen = int.from_bytes(f.read(4), 'big')
        nameoffs = f.tell() + int.from_bytes(f.read(4), 'big') - 8
        commentoffs = f.tell() + int.from_bytes(f.read(4), 'big') - 12
        if commentoffs < f.tell():  # If there's no comment, the value is 0, so if we subtract 12 we'll be at a smaller offset
            commentoffs = 0
        backupoffset = f.tell()

        # Go to the code and read it
        f.seek(codeoffs)
        code = f.read(codelen * 8).hex().upper()  # Convert to uppercase string

        # Split the code with space and newlines
        assembledcode = ''
        for index, char in enumerate(code):
            if index % 16 == 0 and index:
                assembledcode = '\n'.join([assembledcode, char])
            elif index % 8 == 0 and index:
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
            codename += char.decode('utf-8')

        # Go the comment and read it
        comment = ''
        if commentoffs:
            f.seek(commentoffs)
            while f.tell() < filelen:
                char = f.read(1)
                if char == b'\0':
                    break
                comment += char.decode('utf-8')

        # Create the tree widget
        newitem = ModdedTreeWidgetItem(codename, False, True)
        newitem.setText(1, assembledcode)
        newitem.setText(2, comment)
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
    unkcount = 0
    finalist = []

    # Set the lineedit widget
    gidinput = codelist.gidInput
    listwidget = codelist.Codelist

    # First, let's get the file's length
    filelen = f.tell() - 8  # Ignore the F0 line
    f.seek(8)  # Go back to the beginning and skip the GCT magic

    # Verify the gameid's validity
    if 4 <= len(filename) <= 6:
        gidinput.setText(filename)

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

            # Add the line. Yes PyCharm, i know newitem could be referenced before assignment, but currentcode is never
            # true when the loop begins, so shut the fuck up.
            newitem.setText(1, newitem.text(1) + line.hex().upper())
            if amount > 0:
                amount -= 1

        # It's a new code!
        else:
            # Create the tree widget item
            name = 'Unknown Code '
            unkcount += 1
            while listwidget.findItems(name + str(unkcount), Qt.MatchExactly):
                unkcount += 1
            name += str(unkcount)
            newitem = ModdedTreeWidgetItem(name, False, True)
            newitem.setText(1, line.hex().upper())
            finalist.append(newitem)

            # Check the codetype. If the line isn't listed here, it will be added as a single line if found standalone.
            # Type 06 (length specified by code)
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

            # Type C0/C2, F2 (length specified by code)
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
    listwidget.addTopLevelItems(finalist)

    # TODO: LOOK UP DATABASES AND APPLY NAMES, CODES WITH THE SAME NAME ARE TO BE MERGED


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

        # If there are no matches, it means there's no codehandler here
        if not sections:
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Critical, 'Empty DOL', "No GCTs were found in this file", QtWidgets.QMessageBox.Ok).exec_()
            return

        for section in sections:
            # Get the section offset and length
            f.seek(4 * section)
            sectionoffset = int(f.read(4).hex(), 16)
            f.seek(144 + section * 4)
            sectionend = sectionoffset + int(f.read(4).hex(), 16)

            # Initialize vars
            shouldadd = False
            buffer = b'\0\xd0\xc0\xde' * 2

            # Read the section
            f.seek(sectionoffset)
            while f.tell() < sectionend:
                # We found the gct magic, so add this to the buffer
                if shouldadd:
                    buffer += f.read(8)

                # Found the GCT magic, start reading from here
                elif f.read(8) == b'\0\xd0\xc0\xde' * 2:
                    shouldadd = True

                # Found the end of codelist marker, stop reading
                elif shouldadd and f.read(8) == b'\xf0' + b'\0' * 7:
                    buffer += b'\xf0' + b'\0' * 7
                    break

            # Write the buffer to a temporary file, then feed it to the GCT parser
            with open('tmp.gct', 'wb+') as g:
                g.write(buffer)
                g.seek(0, 2)
                ParseGCT('tmp.gct', g, codelist)

            # Remove the file
            os.remove('tmp.gct')

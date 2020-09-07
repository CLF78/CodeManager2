"""
This files contains multiple functions to export codelists.
"""
import os
import re
from binascii import unhexlify

from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from common import CountCheckedCodes


def WriteCheck(filename: str, silent: bool):
    """
    This function performs a couple preliminary operations before importing can take place. Very informative, i know.
    """
    # Check if we can write the file. If not, trigger an error message.
    if not os.access(filename, os.W_OK):
        if not silent:
            QtWidgets.QMessageBox.critical(globalstuff.mainWindow, 'File Write Error', "Can't write file " + filename)
        return False
    return True


def WriteItems(f, enabledlist, depth):
    """
    This recursive function is used by the TXT exporter. So much fun.
    """
    for item in enabledlist:

        # It's a category. Write it only if it's not empty.
        if not item.text(1):
            if item.childCount():
                f.write(''.join(['#' * depth, item.text(0), '\n\n']))  # Add the hashtags if we're in a nested category
                WriteItems(f, [item.child(i) for i in range(item.childCount())], depth + 1)  # Recursive :o

        # It's a code
        else:

            # Write the code name
            f.write(item.text(0))

            # If the code has an author, add it between "[]"
            if item.text(4):
                f.write(''.join([' [', item.text(4), ']']))

            # If the code is enabled, add an asterisk at the beginning of each line
            if item.checkState(0) == Qt.Checked:
                f.writelines(['\n* ' + line for line in item.text(1).splitlines()])

            # Otherwise just add a new line and write the entire code
            else:
                f.write('\n')
                f.write(item.text(1))

            # Add the comment if it exists, preceded by a newline
            if item.text(2):
                f.write('\n')
                f.write(item.text(2))

            # Add the final padding newlines
            f.write('\n\n')

    # We have reached the end of the list (or category). If we're in the latter, write the category escape character and the newlines
    if depth > 0:
        f.write('#' * depth)
        f.write('\n\n')


def InvalidCharacter(name: str, line: int, char: list):
    msgbox = QtWidgets.QMessageBox.question(globalstuff.mainWindow, 'Invalid Line', ''.join(['Invalid character "<b>', char,
                                                                                             '</b>" in code "<b>', name,
                                                                                             '</b>" in line <b>', str(line),
                                                                                             '</b>. Continue exporting?']))
    return msgbox


def ExportTXT(filename: str, source: CodeList, silent: bool):
    # Open the file
    f = open(filename, 'w')

    # Now that we opened the file, we can check if it can be written.
    if not WriteCheck(filename, silent):
        f.close()
        os.remove(filename)
        return False

    # Initialize vars
    enabledlist = source.TreeWidget.findItems('', Qt.MatchContains)

    # Write the game id and name
    f.write('\n'.join([source.gameID, source.gameName, '']))

    # Write the codes!
    WriteItems(f, enabledlist, 0)

    # Remove the extra newline at the end, then close the file!
    f.seek(f.tell() - 2)  # We have to use seek type 0 or the program will crash
    f.truncate()
    f.close()
    return True


def ExportINI(filename: str, source: CodeList, silent: bool):
    """
    The simplest export function so far. A real piece of cake.
    """
    # Open the file. Not using "with" here due to error handling later on
    f = open(filename, 'w')

    # Now that we opened the file, we can check if it can be written.
    if not WriteCheck(filename, silent):
        f.close()
        os.remove(filename)
        return False

    # Initialize vars
    linerule = re.compile('^[\dA-F]{8} [\dA-F]{8}$', re.I | re.M)  # Ignore case + multiple lines
    enabledlist = filter(lambda x: bool(x.text(1)), source.TreeWidget.findItems('', Qt.MatchContains | Qt.MatchRecursive))
    geckostr = '[Gecko]'
    geckoenabledstr = '\n[Gecko_Enabled]'  # Adding a new line because it's not at the beginning of the file

    # Assemble the giant strings
    for item in enabledlist:

        # Add code name, code and author if present. Code must be lowercase because Dolphin.
        if item.text(4):
            geckostr = ''.join([geckostr, '\n$', item.text(0), ' [', item.text(4), ']\n', item.text(1).lower()])
        else:
            geckostr = ''.join([geckostr, '\n$', item.text(0), '\n', item.text(1).lower()])

        # Add comment if present
        if item.text(2):
            for line in item.text(2).splitlines():
                geckostr = '\n*'.join([geckostr, line])
        else:
            geckostr += '\n*'

        # Add to Gecko_Enabled if checked, but only if the code is valid
        if item.checkState(0) == Qt.Checked and len(re.findall(linerule, item.text(1))) == item.text(1).count('\n') + 1:
            geckoenabledstr = '\n$'.join([geckoenabledstr, item.text(0)])

    # Write the codes!
    f.write(geckostr)

    # Only write gecko enabled if at least one code is enabled
    if len(geckoenabledstr) > 16:
        f.write(geckoenabledstr)

    # Autosaved data was found, ask the user what they want to do with it.
    if source.scrap:
        if not silent:
            msgbox = QtWidgets.QMessageBox.question(globalstuff.mainWindow, 'Additional Data Found',
                                                    'Additional data was found in a previously imported .ini file.'
                                                    'Port the data over to this file?')
        if silent or msgbox == QtWidgets.QMessageBox.Yes:
            f.write('\n')
            f.write(source.scrap)
            source.scrap = ''

    # Write the final newline and close the file. Time to pack up and go home.
    f.write('\n')
    f.close()
    return True


def ExportGCT(filename: str, source: CodeList, silent: bool):
    """
    Exports a GCT in the regular format (screw BrawlBox)
    """
    # Open the file. Not using "with" here due to error handling later on
    f = open(filename, 'wb')

    # Now that we opened the file, we can check if it can be written.
    if not WriteCheck(filename, silent):
        f.close()
        os.remove(filename)
        return False

    # Initialize vars
    charrule = re.compile('[\d A-F]', re.I)
    linerule = re.compile('^[\dA-F]{8} [\dA-F]{8}$', re.I)
    enabledlist = filter(lambda x: bool(x.text(1)), CountCheckedCodes(source.TreeWidget, True))

    # Write the gct!
    f.write(globalstuff.gctmagic)
    for item in enabledlist:
        code = item.text(1).splitlines()  # Remove newlines
        currline = 1
        for line in code:

            # Make sure there are no non-hex characters
            if re.match(linerule, line):
                f.write(unhexlify(line.replace(' ', '')))  # Didn't strip spaces earlier for line count purposes ;)
                currline += 1

            # There's an invalid character! FIND HIM!
            else:
                char = re.sub(charrule, '', line)[0]

                # Caught the offender. You're under arrest!
                if not silent and InvalidCharacter(item.text(0), currline, char) == QtWidgets.QMessageBox.No:
                    f.close()
                    os.remove(filename)  # Remove the incomplete file
                    return False
                else:
                    f.seek(-8 * currline, 1)  # Go back to the beginning of this code
                    f.truncate()  # Remove all lines after it, the code is broken
                    break  # Go to next code

    # Finish it off
    f.write(globalstuff.gctend)
    flen = f.tell()
    f.close()

    # If we didn't write anything at all, might as well remove the file
    if flen == 16:
        os.remove(filename)
        return False
    return True

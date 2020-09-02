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


def WriteCheck(filename: str):
    """
    This function performs a couple preliminary operations before importing can take place. Very informative, i know.
    """
    # Check if we can write the file. If not, trigger an error message.
    if not os.access(filename, os.W_OK):
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle('File Write Error')
        msgbox.setText("Can't write file " + filename)
        msgbox.exec_()
        return False
    return True


def InvalidCharacter(name: str, line: int, char: list):
    msgbox = QtWidgets.QMessageBox()
    msgbox.setWindowTitle('Invalid Line')
    msgbox.setText(''.join(['Invalid character "<b>', char, '</b>" in code "<b>', name, '</b>" in line <b>', str(line), '</b>. Continue exporting?']))
    msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    ret = msgbox.exec_()
    return ret


def ExportTXT(filename, source):
    if not WriteCheck(filename):
        return
    print('sos')


def ExportINI(filename, source):
    """
    The simplest export function so far. A real piece of cake.
    """
    # Initialize vars
    linerule = re.compile('^[\dA-F]{8} [\dA-F]{8}$', re.I | re.M)  # Ignore case + multiple lines
    enabledlist = filter(lambda x: bool(x.text(1)), source.Codelist.findItems('', Qt.MatchContains | Qt.MatchRecursive))
    geckostr = '[Gecko]'
    geckoenabledstr = '\n[Gecko_Enabled]'  # Adding a new line because it's not at the beginning of the file

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

    # Open the file. Not using "with" here due to error handling later on
    f = open(filename, 'w')

    # Now that we opened the file, we can check if it can be written.
    if not WriteCheck(filename):
        return

    # Write the codes!
    f.write(geckostr)

    # Only write gecko enabled if at least one code is enabled
    if len(geckoenabledstr) > 16:
        f.write(geckoenabledstr)

    # Autosaved data was found, ask the user what they want to do with it.
    if source.scrap:
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle('Additional Data Found')
        msgbox.setText('Additional data was found in a previously imported .ini file. Port the data over to this file?')
        msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        ret = msgbox.exec_()
        if ret == QtWidgets.QMessageBox.Yes:
            f.write('\n')
            f.write(source.Codelist.scrap)
            source.scrap = ''

    # Write the final newline and close the file. Time to pack up and go home.
    f.write('\n')
    f.close()


def ExportGCT(filename: str, source: CodeList):
    """
    Exports a GCT in the regular format (screw BrawlBox)
    """
    # Initialize vars
    linerule = re.compile('^[\dA-F]{8} [\dA-F]{8}$', re.I)
    charrule = re.compile('[\d A-F]', re.I)
    enabledlist = filter(lambda x: bool(x.text(1)), CountCheckedCodes(source.Codelist, True))

    # Open the file. Not using "with" here due to error handling later on
    f = open(filename, 'wb')

    # Now that we opened the file, we can check if it can be written.
    if not WriteCheck(filename):
        return

    # Write the gct!
    f.write(globalstuff.gctmagic)
    for item in enabledlist:
        code = item.text(1).splitlines()  # Remove newlines
        currline = 1
        for line in code:

            # Make sure there are no non-hex characters
            if re.match(linerule, line):
                f.write(unhexlify(line.replace(' ', '')))  # Didn't strip spaces earlier for line count purposes ;)

            # There's an invalid character! FIND HIM!
            else:
                for char in line:
                    if not re.match(charrule, char):
                        break

                # Caught the offender. Also, something about a variable referenced before assignment. Not gonna write
                # another rant about that shit.
                if InvalidCharacter(item.text(0), currline, char) == QtWidgets.QMessageBox.No:
                    f.close()
                    os.remove(filename)  # Remove the incomplete file
                    return
                else:
                    f.seek(-8 * currline, 1)  # Go back to the beginning of this code
                    f.truncate()  # Remove all lines after it, the code is broken
                    break  # Go to next code
            currline += 1
        f.write(globalstuff.gctend)
        flen = f.tell()
        f.close()

        # If we didn't write anything at all, might as well remove the file
        if flen == 16:
            os.remove(filename)

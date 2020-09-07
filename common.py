"""
This file contains functions that are used by multiple windows to prevent duplication.
"""
from PyQt5.Qt import Qt
from PyQt5 import QtWidgets

import globalstuff


def GameIDMismatch():
    msgbox = QtWidgets.QMessageBox.question(globalstuff.mainWindow, 'Game ID Mismatch',
                                            "The Game ID in this codelist doesn't match this file's."
                                            "Do you want to continue?")
    return msgbox


def CheckChildren(item: QtWidgets.QTreeWidgetItem):
    """
    Recursively enables the check on an item's children
    """
    for i in range(item.childCount()):
        child = item.child(i)
        if child.childCount():
            CheckChildren(child)
        else:
            child.setCheckState(0, Qt.Checked)


def CountCheckedCodes(source: QtWidgets.QTreeWidget, userecursive: bool):
    """
    Returns a list of the codes currently enabled, based on certain criteria. Matchflag returns 64 if userecursive is
    False, 1 if True.
    """
    return filter(lambda x: bool(x.checkState(0)), source.findItems('', Qt.MatchContains | Qt.MatchFlag(64 >> 6 * int(not userecursive))))


def SelectItems(source: QtWidgets.QTreeWidget):
    """
    Marks items as checked if they are selected, otherwise unchecks them
    """
    bucketlist = source.findItems('', Qt.MatchContains | Qt.MatchRecursive)
    for item in bucketlist:
        if item in source.selectedItems():
            item.setCheckState(0, Qt.Checked)
        else:
            item.setCheckState(0, Qt.Unchecked)

    # This for categories which aren't expanded
    for item in filter(lambda x: x in source.selectedItems() and x.childCount() and not x.isExpanded(), bucketlist):
        CheckChildren(item)


def CleanChildren(item: QtWidgets.QTreeWidgetItem):
    """
    The clone function duplicates unchecked children as well, so we're cleaning those off. I'm sorry, little ones.
    """
    for i in range(item.childCount()):
        child = item.child(i)
        if child:  # Failsafe
            if child.childCount():
                CleanChildren(child)
            elif child.checkState(0) == Qt.Unchecked:
                item.takeChild(i)


def AssembleCode(code: str):
    """
    Takes an unformatted string and adds spaces and newlines.
    """
    assembledcode = ''
    for index, char in enumerate(code):
        if not index % 16 and index:
            assembledcode = '\n'.join([assembledcode, char.upper()])
        elif not index % 8 and index:
            assembledcode = ' '.join([assembledcode, char.upper()])
        else:
            assembledcode = ''.join([assembledcode, char.upper()])
    return assembledcode

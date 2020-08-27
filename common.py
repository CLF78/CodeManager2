"""
This file contains functions that are used by multiple windows to prevent duplication.
"""
from PyQt5.Qt import Qt
from PyQt5 import QtWidgets


def GameIDMismatch():
    msgbox = QtWidgets.QMessageBox()
    msgbox.setWindowTitle('Game ID Mismatch')
    msgbox.setText("The Game ID in this codelist doesn't match this file's. Do you want to continue?")
    msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
    msgbox.setDefaultButton(QtWidgets.QMessageBox.Yes)
    ret = msgbox.exec_()
    return ret


def CheckChildren(item):
    """
    Recursively enables the check on an item's children
    """
    for i in range(0, item.childCount()):
        child = item.child(i)
        if child.childCount():
            CheckChildren(child)
        else:
            child.setCheckState(0, Qt.Checked)


def CountCheckedCodes(source, userecursive: bool):
    """
    Returns a list of the codes currently enabled, based on certain criteria.
    """
    userecursive = not userecursive
    enabledlist = []
    for item in source.findItems('', Qt.MatchContains | Qt.MatchFlag(64 >> 6 * userecursive)):  # This returns 64 if False, 1 if True
        if item.checkState(0) > 0:  # We're looking for both partially checked and checked items
            enabledlist.append(item)
    return enabledlist


def SelectItems(source):
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
    for item in bucketlist:
        if item in source.selectedItems() and item.childCount() and not item.isExpanded():
            CheckChildren(item)

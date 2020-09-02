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
    ret = msgbox.exec_()
    return ret


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
    userecursive = not userecursive
    return filter(lambda x: bool(x.checkState(0)), source.findItems('', Qt.MatchContains | Qt.MatchFlag(64 >> 6 * userecursive)))


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

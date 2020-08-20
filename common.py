"""
This file contains functions that are used by multiple windows to prevent duplication.
"""
from PyQt5.Qt import Qt


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


def CountCheckedCodes(source, dontuserecursive: bool):
    """
    Returns a list of the codes currently enabled, based on certain criteria.
    """
    enabledlist = []
    for item in source.findItems('', Qt.MatchContains | Qt.MatchFlag(64 >> 6 * dontuserecursive)):  # This returns 64 if False, 1 if True
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

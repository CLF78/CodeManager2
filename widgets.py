"""
This file contains modified widgets used by various windows.
"""
import globalstuff
from PyQt5 import QtWidgets, QtGui
from PyQt5.Qt import Qt


class ModdedTreeWidget(QtWidgets.QTreeWidget):
    """
    This modded tree widget lets me move codes between subwindows without losing data
    """
    def __init__(self):
        super().__init__()

        # Set flags
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setHeaderHidden(True)
        self.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked)
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        """
        This forces the widget to accept drops, which would otherwise be rejected due to the InternalMove flag.
        """
        src = e.source()
        if isinstance(src, QtWidgets.QTreeWidget) or isinstance(src, ModdedTreeWidget):
            e.accept()

    def dropEvent(self, e: QtGui.QDropEvent):
        """
        This bad hack adds a copy of the source widget's selected items in the destination widget. This is due to PyQt
        clearing the hidden columns, which we don't want.
        """
        src = e.source()
        if src is not self:
            for item in src.selectedItems():
                clone = item.clone()
                clone.setFlags(clone.flags() | Qt.ItemIsEditable)
                self.addTopLevelItem(clone)
        QtWidgets.QTreeWidget.dropEvent(self, e)  # Call the original function


class ModdedTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """
    Basically a glorified QTreeWidgetItem, with a couple of improvements that should make them less annoying to use.
    """
    def __init__(self, text: str, iscategory: bool, iseditable: bool):
        super().__init__()

        self.setCheckState(0, Qt.Unchecked)

        if text:
            self.setText(0, text)
        elif iscategory:
            self.setText(0, 'New Category')
        else:
            self.setText(0, 'New Code')

        self.setAsCategory(iscategory)
        self.setAsEditable(iseditable)

    def setAsCategory(self, iscategory: bool):
        if iscategory:
            self.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.ShowIndicator)
            self.setFlags(self.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsDropEnabled)
        else:
            self.setChildIndicatorPolicy(QtWidgets.QTreeWidgetItem.DontShowIndicator)
            self.setFlags(self.flags() ^ Qt.ItemIsDropEnabled ^ Qt.ItemIsAutoTristate)

    def setAsEditable(self, iseditable: bool):
        if iseditable:
            self.setFlags(self.flags() | Qt.ItemIsEditable)
        else:
            self.setFlags(self.flags() ^ Qt.ItemIsEditable)


class ModdedSubWindow(QtWidgets.QMdiSubWindow):
    """
    I just needed to run a function when a closeEvent is triggered, so there we go.
    """
    def __init__(self):
        super().__init__()

    def closeEvent(self, e: QtGui.QCloseEvent):
        QtWidgets.QMdiSubWindow.closeEvent(self, e)
        globalstuff.mainWindow.updateboxes()

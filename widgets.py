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

        # Hide header, enable multiple selection and reordering, add space to the right and set edit trigger to select+click
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
        if isinstance(src, QtWidgets.QTreeWidget):
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
        super().dropEvent(e)  # Call the original function


class ModdedTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """
    Basically a glorified QTreeWidgetItem, with a couple of improvements that should make them less annoying to use.
    """
    def __init__(self, text: str, iscategory: bool, iseditable: bool):
        super().__init__()

        # Set check state
        self.setCheckState(0, Qt.Unchecked)

        # Set default text
        if text:
            self.setText(0, text)
        elif iscategory:
            self.setText(0, 'New Category')
        else:
            self.setText(0, 'New Code')

        # Set flags based on the given directives
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
        elif self.flags() & Qt.ItemIsEditable:
            self.setFlags(self.flags() ^ Qt.ItemIsEditable)


class ModdedSubWindow(QtWidgets.QMdiSubWindow):
    """
    Dark mode and box updating functionality.
    """
    def __init__(self, islist: bool):
        super().__init__()
        self.islist = islist
        self.setWindowIcon(globalstuff.empty)
        self.setAttribute(Qt.WA_DeleteOnClose)

    def setWidget(self, widget: QtWidgets.QWidget):
        """
        Adds a fix for dark theme if it's enabled
        """
        super().setWidget(widget)
        if globalstuff.theme == 'dark':
            w = self.widget()
            w.setPalette(globalstuff.textpal)
            if hasattr(w, 'TreeWidget'):
                w.TreeWidget.setStyleSheet(globalstuff.treeqss)

    def closeEvent(self, e: QtGui.QCloseEvent):
        super().closeEvent(e)
        if self.islist:
            globalstuff.mainWindow.updateboxes()


class ModdedMdiArea(QtWidgets.QMdiArea):
    """
    Modded MdiArea to accept file drops
    """
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        if e.mimeData().hasUrls:
            e.setDropAction(Qt.CopyAction)
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e: QtGui.QDropEvent):
        if e.mimeData().hasUrls():
            e.setDropAction(Qt.CopyAction)
            e.accept()
            links = [str(url.toLocalFile()) for url in e.mimeData().urls()]
            globalstuff.mainWindow.openCodelist(None, links)
        else:
            e.ignore()

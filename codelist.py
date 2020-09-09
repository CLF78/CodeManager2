"""
Codelists are different from databases, as they accept adding/removing, importing/exporting, reordering, dropping
and more.
"""
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codeeditor import CodeEditor, HandleCodeOpen, HandleAddCode, CleanParentz, RenameWindows
from common import CountCheckedCodes, SelectItems, GameIDMismatch, CleanChildren
from titles import TitleLookup
from widgets import ModdedTreeWidget, ModdedTreeWidgetItem


class CodeList(QtWidgets.QWidget):
    def __init__(self, wintitle):
        super().__init__()

        # Create the codelist and connect it to the handlers
        self.TreeWidget = ModdedTreeWidget()
        self.TreeWidget.itemSelectionChanged.connect(self.HandleSelection)
        self.TreeWidget.itemDoubleClicked.connect(lambda x: HandleCodeOpen(x, False))
        self.TreeWidget.itemChanged.connect(RenameWindows)
        self.TreeWidget.itemClicked.connect(self.HandleClicking)

        # Merge button, up here for widget height purposes
        self.mergeButton = QtWidgets.QPushButton('Merge Selected')
        self.mergeButton.clicked.connect(lambda: self.HandleMerge(CountCheckedCodes(self.TreeWidget, True)))

        # Add button+menu
        addMenu = QtWidgets.QMenu()
        deface = addMenu.addAction('Add Code', lambda: HandleAddCode(None, False))
        addMenu.addAction('Add Category', self.HandleAddCategory)
        self.addButton = QtWidgets.QToolButton()
        self.addButton.setDefaultAction(deface)  # Do this if you click the Add button instead of the arrow
        self.addButton.setFixedHeight(self.mergeButton.sizeHint().height())  # Makes this the same height as QPushButton
        self.addButton.setMenu(addMenu)
        self.addButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.addButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)  # Use full widget width
        self.addButton.setText('Add')

        # Sort button+menu
        sortMenu = QtWidgets.QMenu()
        defact = sortMenu.addAction('Alphabetical', lambda: self.TreeWidget.sortItems(0, Qt.AscendingOrder))
        sortMenu.addAction('Alphabetical (Reverse)', lambda: self.TreeWidget.sortItems(0, Qt.DescendingOrder))
        sortMenu.addAction('Size', self.SortListSize)
        self.sortButton = QtWidgets.QToolButton()
        self.sortButton.setDefaultAction(defact)  # Do this if you click the Sort button instead of the arrow
        self.sortButton.setMenu(sortMenu)
        self.sortButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.sortButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)  # Use full widget width
        self.sortButton.setText('Sort')

        # Import, Export and Remove buttons
        self.importButton = QtWidgets.QPushButton('Import List')
        self.exportButton = QtWidgets.QPushButton('Export List')
        self.removeButton = QtWidgets.QPushButton('Remove Selected')
        self.importButton.clicked.connect(lambda: globalstuff.mainWindow.openCodelist(self))
        self.exportButton.clicked.connect(lambda: globalstuff.mainWindow.exportList(self))
        self.removeButton.clicked.connect(self.HandleRemove)

        # Configure the buttons
        self.EnableButtons()

        # Game ID text field + save button
        self.gidInput = QtWidgets.QLineEdit()
        self.gidInput.setPlaceholderText('Insert GameID here...')
        self.gidInput.setMaxLength(6)
        self.gidInput.textEdited.connect(self.UpdateButton)
        self.savegid = QtWidgets.QPushButton('Save')
        self.savegid.setEnabled(False)
        self.savegid.clicked.connect(lambda: self.SetGameID(self.gidInput.text()))

        # Set game id, game name and update the window title accordingly. Also add the scrap
        self.gameID = 'UNKW00'
        self.gameName = 'Unknown Game'
        self.SetGameID(wintitle)
        self.scrap = ''

        # Make a horizontal layout for these two
        hlyt = QtWidgets.QHBoxLayout()
        hlyt.addWidget(self.gidInput)
        hlyt.addWidget(self.savegid)

        # Line counter
        self.lineLabel = QtWidgets.QLabel('Lines: 2')
        self.lineLabel.setAlignment(Qt.AlignRight)

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addLayout(hlyt, 0, 0, 1, 2)
        lyt.addWidget(self.TreeWidget, 1, 0, 1, 2)
        lyt.addWidget(self.lineLabel, 2, 0, 1, 2)
        lyt.addWidget(self.addButton, 3, 0)
        lyt.addWidget(self.sortButton, 3, 1)
        lyt.addWidget(self.mergeButton, 4, 0)
        lyt.addWidget(self.removeButton, 4, 1)
        lyt.addWidget(self.importButton, 5, 0)
        lyt.addWidget(self.exportButton, 5, 1)
        self.setLayout(lyt)

    def AddFromDatabase(self, enabledlist: list, gameid: str):
        """
        Takes a list of the enabled items and clones it in the codelist.
        """
        # Check for game id mismatch and update if necessary
        if gameid != self.gameID:
            if self.gameID != 'UNKW00' and GameIDMismatch() == QtWidgets.QMessageBox.No:
                return
            self.SetGameID(gameid)

        # Add the codes
        for item in enabledlist:
            clone = item.clone()
            clone.setFlags(clone.flags() | Qt.ItemIsEditable)  # Enable renaming
            self.TreeWidget.addTopLevelItem(clone)
            CleanChildren(clone)

        # Update the selection
        self.HandleSelection()
        self.UpdateLines()

    def HandleSelection(self):
        """
        Self explanatory
        """
        SelectItems(self.TreeWidget)
        self.EnableButtons()
        self.UpdateLines()

    def HandleClicking(self, item: QtWidgets.QTreeWidgetItem):
        """
        Backs up the codename and checks the buttons
        """
        item.setStatusTip(0, item.text(0))
        self.EnableButtons()
        self.UpdateLines()

    def EnableButtons(self, canexport=False, canremove=False, canmerge=False):
        """
        Enables the Remove, Export and Merge button if the respective conditions are met
        """
        for item in CountCheckedCodes(self.TreeWidget, True):
            if item.text(1):
                if canexport:
                    canmerge = True
                    break  # All the options are already enabled, no need to parse the list any further
                canexport = True
            canremove = True

        self.removeButton.setEnabled(canremove)
        self.exportButton.setEnabled(canexport)
        self.mergeButton.setEnabled(canmerge)

    def HandleAddCategory(self):
        """
        Adds a new category to the codelist
        """
        newitem = ModdedTreeWidgetItem('', True, True)
        self.TreeWidget.addTopLevelItem(newitem)
        self.TreeWidget.editItem(newitem, 0)  # Let the user rename it immediately

    def SortListSize(self):
        """
        Temporarily removes all items without children, then orders the remaining items alphabetically. The removed
        items will then be ordered by code size and re-added to the tree.
        """
        # Remove all codes
        backuplist = []
        for item in filter(lambda x: bool(x.text(1)), self.TreeWidget.findItems('', Qt.MatchContains)):
            backuplist.append(self.TreeWidget.takeTopLevelItem(self.TreeWidget.indexOfTopLevelItem(item)))

        # Sort the categories alphabetically
        self.TreeWidget.sortItems(0, Qt.AscendingOrder)

        # Sort the backup list by code size (bigger codes first)
        backuplist.sort(key=lambda x: len(x.text(1)), reverse=True)

        # Reinsert the items
        self.TreeWidget.insertTopLevelItems(self.TreeWidget.topLevelItemCount(), backuplist)

    def HandleMerge(self, mergedlist: list):
        """
        Merges codes together
        """
        # Initialize vars
        destination = None
        wlist = [w.widget() for w in globalstuff.mainWindow.mdi.subWindowList() if isinstance(w.widget(), CodeEditor)]

        # Begin working
        for item in filter(lambda x: bool(x.text(1)), mergedlist):

            # We have a destination
            if destination:
                # Merge the codes
                destination.setText(1, '\n'.join([destination.text(1), item.text(1)]))

                # Kill any reference to the item
                CleanParentz(item, wlist)
                if item.parent():
                    item.parent().takeChild(item.parent().indexOfChild(item))
                else:
                    self.TreeWidget.takeTopLevelItem(self.TreeWidget.indexOfTopLevelItem(item))

            # It's the first code in the list, set it as destination
            else:
                destination = item
                destination.setText(2, '')  # Clear the comment, as it no longer applies

        # Now find all instances of CodeEditor that have the destination code open, and update their code widget
        for window in wlist:
            if window.parentz == destination:
                window.setPlainText(destination.text(1))
                return

    def HandleRemove(self):
        """
        Handles item removal. Not much to say here :P
        """
        wlist = [w.widget() for w in globalstuff.mainWindow.mdi.subWindowList() if isinstance(w.widget(), CodeEditor)]
        for item in filter(lambda x: x.checkState(0) == Qt.Checked, CountCheckedCodes(self.TreeWidget, True)):

            # Remove the item
            if item.parent():
                item.parent().takeChild(item.parent().indexOfChild(item))
            else:
                self.TreeWidget.takeTopLevelItem(self.TreeWidget.indexOfTopLevelItem(item))

            # Set all code editor widgets that had this item as parent to None
            if item.text(1):
                CleanParentz(item, wlist)

    def UpdateButton(self):
        """
        Enables the button to save the game id if it's valid
        """
        self.savegid.setEnabled(len(self.gidInput.text()) > 3)

    def SetGameID(self, gameid: str):
        """
        Sets the given game id in the variable, game id text field and window title. Also looks up the game name.
        """
        if 4 <= len(gameid) <= 6:
            self.gameID = gameid
            self.gameName = TitleLookup(gameid)
            self.gidInput.setText(gameid)
        self.savegid.setEnabled(False)
        self.setWindowTitle('Codelist - {} [{}]'.format(self.gameName, gameid if gameid else self.gameID).replace('\n', ''))
        globalstuff.mainWindow.updateboxes()

    def UpdateLines(self):
        """
        Updates the number of total code lines in the list
        """
        lines = 2  # One for the magic and one for the F0 terminator
        for item in filter(lambda x: bool(x.text(1)), CountCheckedCodes(self.TreeWidget, True)):
            lines += item.text(1).count('\n') + 1  # +1 is because the first line doesn't have an "\n" character
        self.lineLabel.setText('Lines: ' + str(lines))

"""
Codelists are different from databases, as they accept adding/removing, importing/exporting, reordering, dropping
and more.
"""
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codeeditor import CodeEditor, HandleCodeOpen, HandleAddCode, CleanParentz
from common import CountCheckedCodes, SelectItems, GameIDMismatch
from titles import TitleLookup
from widgets import ModdedTreeWidget, ModdedTreeWidgetItem


class CodeList(QtWidgets.QWidget):
    def __init__(self, wintitle):
        super().__init__()

        # Create the codelist and connect it to the handlers
        self.Codelist = ModdedTreeWidget()
        self.Codelist.itemSelectionChanged.connect(self.HandleSelection)
        self.Codelist.itemDoubleClicked.connect(HandleCodeOpen)
        self.Codelist.itemChanged.connect(self.RenameWindows)
        self.Codelist.itemClicked.connect(self.HandleClicking)  # Using the status tip as a backup option

        # Merge button, up here for widget height purposes
        self.mergeButton = QtWidgets.QPushButton('Merge Selected')
        self.mergeButton.clicked.connect(lambda: self.HandleMerge(CountCheckedCodes(self.Codelist, True)))

        # Add button+menu
        addMenu = QtWidgets.QMenu()
        deface = addMenu.addAction('Add Code', lambda: HandleAddCode(None))  # Gotta pass the argument, so lambda time
        addMenu.addAction('Add Category', self.HandleAddCategory)
        self.addButton = QtWidgets.QToolButton()
        self.addButton.setDefaultAction(deface)  # Do this if you click the Add button instead of the arrow
        self.addButton.setMenu(addMenu)
        self.addButton.setFixedHeight(self.mergeButton.sizeHint().height())  # Makes this the same height as QPushButton
        self.addButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.addButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)  # Use full widget width
        self.addButton.setText('Add')
        self.addButton.setToolButtonStyle(Qt.ToolButtonTextOnly)

        # Sort button+menu
        sortMenu = QtWidgets.QMenu()
        defact = sortMenu.addAction('Alphabetical', lambda: self.Codelist.sortItems(0, Qt.AscendingOrder))  # The unknown soldier
        sortMenu.addAction('Alphabetical (Reverse)', lambda: self.Codelist.sortItems(0, Qt.DescendingOrder))  # The unknown soldier's sibiling
        sortMenu.addAction('Size', self.SortListSize)
        self.sortButton = QtWidgets.QToolButton()
        self.sortButton.setDefaultAction(defact)  # Do this if you click the Sort button instead of the arrow
        self.sortButton.setMenu(sortMenu)
        self.sortButton.setFixedHeight(self.mergeButton.sizeHint().height())  # Makes this the same height as QPushButton
        self.sortButton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)
        self.sortButton.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)  # Use full widget width
        self.sortButton.setText('Sort')
        self.sortButton.setToolButtonStyle(Qt.ToolButtonTextOnly)

        # Import and Remove buttons
        self.importButton = QtWidgets.QPushButton('Import List')
        self.importButton.clicked.connect(lambda: globalstuff.mainWindow.openCodelist(self))
        self.exportButton = QtWidgets.QPushButton('Export List')
        self.removeButton = QtWidgets.QPushButton('Remove Selected')
        self.removeButton.clicked.connect(self.HandleRemove)

        # Configure the buttons
        self.EnableButtons()

        # Set game id, game name and update the window title accordingly
        self.gameID = 'UNKW00'
        self.gameName = 'Unknown Game'
        self.SetGameID(wintitle)

        # Game ID text field + save button
        self.gidInput = QtWidgets.QLineEdit()
        self.gidInput.setPlaceholderText('Insert GameID here...')
        self.gidInput.setMaxLength(6)
        self.gidInput.setText(self.gameID)
        self.gidInput.textEdited.connect(self.UpdateButton)
        self.savegid = QtWidgets.QPushButton('Save')
        self.savegid.setEnabled(False)
        self.savegid.clicked.connect(lambda: self.SetGameID(self.gidInput.text()))

        # Make a horizontal layout for these two
        formlyt = QtWidgets.QHBoxLayout()
        formlyt.addWidget(self.gidInput)
        formlyt.addWidget(self.savegid)

        # Line counter
        self.lineLabel = QtWidgets.QLabel('Lines: 2')
        self.lineLabel.setAlignment(Qt.AlignRight)

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addLayout(formlyt, 0, 0, 1, 2)
        lyt.addWidget(self.Codelist, 1, 0, 1, 2)
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
            clone.setFlags(clone.flags() | Qt.ItemIsEditable)  # Gotta enable renaming, hehe.
            self.Codelist.addTopLevelItem(clone)
            self.CleanChildren(clone)

        # Update the selection
        self.HandleSelection()
        self.UpdateLines()

    def CleanChildren(self, item: QtWidgets.QTreeWidgetItem):
        """
        The clone function duplicates unchecked children as well, so we're cleaning those off. I'm sorry, little ones.
        """
        for i in range(item.childCount()):
            child = item.child(i)
            if child:  # Failsafe
                if child.childCount():
                    self.CleanChildren(child)
                elif child.checkState(0) == Qt.Unchecked:
                    item.takeChild(i)

    def HandleSelection(self):
        SelectItems(self.Codelist)
        self.EnableButtons()
        self.UpdateLines()

    def HandleClicking(self, item: QtWidgets.QTreeWidgetItem):
        """
        Backups up the codename and checks the buttons
        """
        item.setStatusTip(0, item.text(0))
        self.EnableButtons()
        self.UpdateLines()

    def EnableButtons(self, canexport=False, canremove=False, canmerge=False):
        """
        Enables the Remove, Export and Merge button if the respective conditions are met
        """
        for item in CountCheckedCodes(self.Codelist, True):
            if item.text(1):
                if canexport:
                    canmerge = True
                    break  # All the options are already enabled, no need to parse the list any further
                canexport = True
            canremove = True

        self.removeButton.setEnabled(canremove)
        self.exportButton.setEnabled(canexport)
        self.mergeButton.setEnabled(canmerge)

    @staticmethod
    def RenameWindows(item: QtWidgets.QTreeWidgetItem):
        """
        When you rename a code, the program will look for code editors that originated from that code and update their
        window title accordingly
        """
        # First, verify that the name is not empty. If so, restore the original string and clear the backup.
        if not item.text(0):
            item.setText(0, item.statusTip(0))
            item.setStatusTip(0, '')
            return  # Since there was no update, we don't need to run the below stuff

        # Do the rename
        for window in [window for window in globalstuff.mainWindow.mdi.subWindowList() if isinstance(window.widget(), CodeEditor) and window.widget().parentz == item]:
            if item.text(4):
                window.widget().setWindowTitle('Code Editor - {} [{}]'.format(item.text(0), item.text(4)))
            else:
                window.widget().setWindowTitle('Code Editor - {}'.format(item.text(0)))

    def HandleAddCategory(self):
        """
        Adds a new category to the codelist
        """
        newitem = ModdedTreeWidgetItem('', True, True)
        self.Codelist.addTopLevelItem(newitem)
        self.Codelist.editItem(newitem, 0)  # Let the user rename it immediately

    def SortListSize(self):
        """
        Temporarily removes all items without children, then orders the remaining items alphabetically. The removed
        items will then be ordered by code size and re-added to the tree.
        """
        # Remove all codes
        backuplist = []
        for item in filter(lambda x: bool(x.text(1)), self.Codelist.findItems('', Qt.MatchContains)):
            backuplist.append(self.Codelist.takeTopLevelItem(self.Codelist.indexOfTopLevelItem(item)))

        # Sort the categories alphabetically
        self.Codelist.sortItems(0, Qt.AscendingOrder)

        # Sort the backup list by code size (bigger codes first)
        backuplist.sort(key=lambda x: len(x.text(1)), reverse=True)

        # Reinsert the items
        self.Codelist.insertTopLevelItems(self.Codelist.topLevelItemCount(), backuplist)

    def HandleMerge(self, mergedlist: list):
        """
        Merges codes together
        """
        destination = None
        for item in filter(lambda x: bool(x.text(1)), mergedlist):

            # We have a destination
            if destination:
                destination.setText(1, '\n'.join([destination.text(1), item.text(1)]))  # Merge the codes
                CleanParentz(item)
                if item.parent():
                    item.parent().takeChild(item.parent().indexOfChild(item))  # It's a child, tell the parent to kill him
                else:
                    self.Codelist.takeTopLevelItem(self.Codelist.indexOfTopLevelItem(item))  # It's a parent, tell the codelist to kill him

            # It's the first code in the list, set it as destination
            else:
                destination = item
                destination.setText(2, '')  # Clear the comment and the placeholder lists, as they no longer apply
                destination.setText(3, '')

        # Now find all instances of CodeEditor that have the destination code open, and update their code widget
        winlist = [window.widget().CodeContent for window in globalstuff.mainWindow.mdi.subWindowList() if isinstance(window.widget(), CodeEditor) and window.widget().parentz == destination]
        for window in winlist:
            window.setPlainText(destination.text(1))

    def HandleRemove(self):
        """
        Handles item removal. Not much to say here :P
        """
        for item in filter(lambda x: x.checkState(0) == Qt.Checked, CountCheckedCodes(self.Codelist, True)):

            # Remove the item
            if item.parent():
                item.parent().takeChild(item.parent().indexOfChild(item))
            else:
                self.Codelist.takeTopLevelItem(self.Codelist.indexOfTopLevelItem(item))

            # Set all code editor widgets that had this item as parent to None
            CleanParentz(item)

    def UpdateButton(self):
        """
        Enables the button to save the game id if it's valid
        """
        if len(self.gidInput.text()) > 3:
            self.savegid.setEnabled(True)
        else:
            self.savegid.setEnabled(False)

    def SetGameID(self, gameid: str):
        """
        Sets the given game id in the variable, game id text field and window title. Also looks up the game name.
        """
        if 4 <= len(gameid) <= 6:
            self.gameID = gameid
            self.gameName = TitleLookup(gameid)
            self.gidInput.setText(gameid)
        self.setWindowTitle('Codelist - {} [{}]'.format(self.gameName, self.gameID))

    def UpdateLines(self):
        """
        Updates the number of total code lines in the list
        """
        lines = 2  # One for the magic and one for the F0 terminator
        for item in filter(lambda x: bool(x.text(1)), CountCheckedCodes(self.Codelist, True)):
            lines += item.text(1).count('\n') + 1  # +1 is because the first line doesn't have an "\n" character
        self.lineLabel.setText('Lines: ' + str(lines))

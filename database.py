"""
Databases are basically read-only lists of codes read from an xml, which adds extra information to the manager.
"""
import os
import shutil
import urllib.request
from typing import Optional

from lxml import etree
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from codeeditor import HandleCodeOpen, CleanParentz
from common import CountCheckedCodes, SelectItems
from titles import TitleLookup
from widgets import ModdedTreeWidgetItem, ModdedSubWindow


class Database(QtWidgets.QWidget):
    def __init__(self, name):
        super().__init__()

        # Create the Database Browser and connect it to the handlers
        self.DBrowser = QtWidgets.QTreeWidget()
        self.DBrowser.itemSelectionChanged.connect(self.HandleSelection)
        self.DBrowser.itemDoubleClicked.connect(HandleCodeOpen)
        self.DBrowser.itemClicked.connect(self.EnableButtons)

        # Set the proper flags
        self.DBrowser.setHeaderHidden(True)
        self.DBrowser.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.DBrowser.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        header = self.DBrowser.header()  # The following leaves some space on the right, to allow dragging the selection
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # Add the search bar
        self.SearchBar = QtWidgets.QLineEdit()
        self.SearchBar.setPlaceholderText('Search codes...')
        self.SearchBar.textEdited.connect(self.HandleSearch)

        # Add the opened codelist combo box
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')
        globalstuff.mainWindow.updateboxes()

        # Finally, add the "Add" button
        self.AddButton = QtWidgets.QPushButton('Add to Codelist')
        self.AddButton.setEnabled(False)
        self.AddButton.clicked.connect(self.HandleAdd)

        # Finally, add the "Update" button
        self.UpdateButton = QtWidgets.QPushButton('Download Updates')

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.SearchBar, 0, 0, 1, 2)
        lyt.addWidget(self.DBrowser, 1, 0, 1, 2)
        lyt.addWidget(self.Combox, 2, 0)
        lyt.addWidget(self.AddButton, 2, 1)
        lyt.addWidget(self.UpdateButton, 3, 0, 1, 2)
        self.setLayout(lyt)

        # Open the database
        self.dbfile = name
        tree = etree.parse(name).getroot()

        # Parse game id, lookup the corresponding name, then apply them to the window title
        try:
            self.gameID = tree.xpath('id')[0].text
            self.gameName = TitleLookup(self.gameID)
        except:
            self.gameID = 'UNKW00'  # Failsafe
            self.gameName = 'Unknown Game'
        self.setWindowTitle('Database Browser - {} [{}]'.format(self.gameName, self.gameID))

        # Add the update url and enable the button if present
        try:
            self.ver = int(tree.xpath('update')[0].attrib['version'])
            self.updateURL = tree.xpath('update')[0].text
        except:
            self.ver = 0
            self.updateURL = ''

        self.UpdateButton.setEnabled(bool(self.updateURL))

        # Import the codes
        self.ParseDatabase(tree.xpath('category') + tree.xpath('code'), None, 3)  # The second tree is because there can be codes without a category

    def ParseDatabase(self, tree: etree, parent: Optional[QtWidgets.QTreeWidgetItem], depth: int):
        """
        Recursively create the code tree based on the xml
        """
        for entry in tree:
            newitem = ModdedTreeWidgetItem(entry.attrib['name'], False, False)  # Assume it's not a category, codes are more common

            # Determine parenthood
            if parent:
                parent.addChild(newitem)
            else:
                self.DBrowser.addTopLevelItem(newitem)

            # Determine type of entry
            if entry.tag == 'category':
                newitem.setAsCategory(True)
                self.ParseDatabase(entry, newitem, depth + 1)
            elif entry.tag == 'code':
                newitem.setText(1, entry[0].text[1:-depth].upper())
                newitem.setText(2, entry.attrib['comment'])
                newitem.setText(3, str([(pl.attrib['letter'],
                                         int(pl.attrib['type']),
                                         pl.attrib['comment'],
                                         pl.attrib['args'].split(',')) for pl in entry.xpath('placeholder')]))
                newitem.setText(4, entry.attrib['author'])

    def HandleSelection(self):
        # Do the selection
        SelectItems(self.DBrowser)
        self.EnableButtons()

    def EnableButtons(self):
        # Update the Add button
        if CountCheckedCodes(self.DBrowser, False):
            self.AddButton.setEnabled(True)
        else:
            self.AddButton.setEnabled(False)

    def HandleSearch(self, text: str):
        """
        Filters codes based on a given string
        """
        for item in self.DBrowser.findItems('', Qt.MatchContains | Qt.MatchRecursive):
            item.setHidden(True)  # Hide all items
            if text.lower() in item.text(0).lower() and item.text(1):
                item.setHidden(False)  # Unhide the item if it's a code and it the text matches, then unhide its parents
                self.UnhideParent(item)

    def UnhideParent(self, item: QtWidgets.QTreeWidgetItem):
        """
        Recursively unhides a given item's parents
        """
        if item.parent():
            item.parent().setHidden(False)
            self.unhideParent(item.parent())

    def HandleAdd(self):
        """
        Transfers the selected codes to the chosen codelist
        """
        enabledlist = CountCheckedCodes(self.DBrowser, False)
        if self.Combox.currentIndex() > 0:
            self.Combox.currentData().AddFromDatabase(enabledlist, self.gameID)
        else:
            win = ModdedSubWindow()
            win.setWidget(CodeList(''))
            win.widget().AddFromDatabase(enabledlist, self.gameID)
            win.setAttribute(Qt.WA_DeleteOnClose)
            globalstuff.mainWindow.mdi.addSubWindow(win)
            win.show()

    def UpdateDatabase(self):
        """
        Updates the database from the given url.
        """
        # Download the file
        try:
            with urllib.request.urlopen(self.updateURL) as src, open('tmp.xml', 'wb') as dst:
                dst.write(src.read())
        except:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Download Error')
            msgbox.setText('There was an error during the database download. Retry?')
            msgbox.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            ret = msgbox.exec_()
            if ret == QtWidgets.QMessageBox.Yes:
                self.UpdateDatabase()
            else:
                return

        # Get the tree and the version
        tree = etree.parse('tmp.xml').getroot()
        ver = int(tree.xpath('update')[0].attrib['version'])

        # Check that the version is newer, otherwise exit
        if ver <= self.ver:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Up to date')
            msgbox.setText('Database is up to date!')
            msgbox.exec_()
            os.remove('tmp.xml')
            return
        else:
            self.ver = ver

        # Clean the parentz parameter of affected Code Editors
        for item in filter(lambda x: bool(x.text(1)), self.DBrowser.findItems('', Qt.MatchContains | Qt.MatchRecursive)):
            CleanParentz(item)

        # Clear the tree and import the codes
        self.DBrowser.clear()
        self.ParseDatabase(tree.xpath('category') + tree.xpath('code'), None, 3)

        # Overwrite the original name and disable the update button, since we don't need it.
        shutil.move('tmp.xml', self.dbfile)
        self.UpdateButton.setEnabled(False)

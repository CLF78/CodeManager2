"""
Databases are basically read-only lists of codes read from an xml, which adds extra information to the manager.
"""
import os
import shutil
import urllib.request
from pkg_resources import parse_version as vercomp
from typing import Optional

from lxml import etree
from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from codeeditor import CodeEditor, HandleCodeOpen, CleanParentz
from common import CountCheckedCodes, SelectItems
from titles import TitleLookup
from widgets import ModdedTreeWidgetItem, ModdedSubWindow


class Database(QtWidgets.QWidget):
    def __init__(self, name):
        super().__init__()

        # Create the Database Browser and connect it to the handlers
        self.TreeWidget = QtWidgets.QTreeWidget()
        self.TreeWidget.itemSelectionChanged.connect(self.HandleSelection)
        self.TreeWidget.itemDoubleClicked.connect(lambda x: HandleCodeOpen(x, True))
        self.TreeWidget.itemClicked.connect(self.EnableButtons)

        # Set the proper flags
        self.TreeWidget.setHeaderHidden(True)
        self.TreeWidget.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.TreeWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        header = self.TreeWidget.header()  # The following leaves some space on the right, to allow dragging the selection
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # Add the search bar
        self.SearchBar = QtWidgets.QLineEdit()
        self.SearchBar.setPlaceholderText('Search codes...')
        self.SearchBar.textEdited.connect(self.HandleSearch)

        # Add the opened codelist combo box
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')

        # Finally, add the "Add" button
        self.AddButton = QtWidgets.QPushButton('Add to Codelist')
        self.AddButton.setEnabled(False)
        self.AddButton.clicked.connect(self.HandleAdd)

        # Finally, add the "Update" button
        self.UpdateButton = QtWidgets.QPushButton('Download Updates')
        self.UpdateButton.clicked.connect(self.UpdateDatabase)

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.SearchBar, 0, 0, 1, 2)
        lyt.addWidget(self.TreeWidget, 1, 0, 1, 2)
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

        # Add the update url
        try:
            self.ver = tree.xpath('update')[0].attrib['version']
            self.updateURL = tree.xpath('update')[0].text
        except:
            self.ver = '0'
            self.updateURL = ''

        # Enable the update button if an url present
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
                self.TreeWidget.addTopLevelItem(newitem)

            # Determine type of entry
            if entry.tag == 'category':
                newitem.setAsCategory(True)
                self.ParseDatabase(entry, newitem, depth + 1)
            elif entry.tag == 'code':
                newitem.setText(1, entry[0].text[1:-depth].upper())
                newitem.setText(2, entry.attrib['comment'])
                newitem.setText(4, entry.attrib['author'])

    def HandleSelection(self):
        # Do the selection
        SelectItems(self.TreeWidget)
        self.EnableButtons()

    def EnableButtons(self):
        # Update the Add button
        if list(CountCheckedCodes(self.TreeWidget, False)):
            self.AddButton.setEnabled(True)
        else:
            self.AddButton.setEnabled(False)

    def HandleSearch(self, text: str):
        """
        Filters codes based on a given string
        """
        for item in self.TreeWidget.findItems('', Qt.MatchContains | Qt.MatchRecursive):
            # Hide all items
            item.setHidden(True)

            # Unhide the item if its name or code match, then unhide its parents
            if item.text(1) and text.lower() in item.text(0).lower() or text.lower() in item.text(1).lower():
                item.setHidden(False)
                self.UnhideParent(item)

    def UnhideParent(self, item: QtWidgets.QTreeWidgetItem):
        """
        Recursively unhides a given item's parents
        """
        if item.parent():
            item.parent().setHidden(False)
            self.UnhideParent(item.parent())

    def HandleAdd(self):
        """
        Transfers the selected codes to the chosen codelist
        """
        enabledlist = CountCheckedCodes(self.TreeWidget, False)
        if self.Combox.currentIndex() > 0:
            self.Combox.currentData().AddFromDatabase(enabledlist, self.gameID)
        else:
            win = ModdedSubWindow()
            win.setWidget(CodeList(self.gameID))
            win.widget().AddFromDatabase(enabledlist, self.gameID)
            globalstuff.mainWindow.mdi.addSubWindow(win)
            globalstuff.mainWindow.updateboxes()
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

        # Get the tree and the version. If the program fails to do so, quietly exit
        try:
            tree = etree.parse('tmp.xml').getroot()
            ver = tree.xpath('update')[0].attrib['version']
        except:
            os.remove('tmp.xml')
            return

        # Check that the new version is actually newer, otherwise exit
        if vercomp(ver) <= vercomp(self.ver):
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Up to date')
            msgbox.setText('Database is up to date!')
            msgbox.exec_()
            os.remove('tmp.xml')
            return

        # Change the string
        self.ver = ver

        # Clean the parentz parameter of affected Code Editors
        # The window list is created earlier so it isn't generated a gazillion times in the for loop
        wlist = [w.widget() for w in globalstuff.mainWindow.mdi.subWindowList() if isinstance(w.widget(), CodeEditor)]
        for item in filter(lambda x: bool(x.text(1)), self.TreeWidget.findItems('', Qt.MatchContains | Qt.MatchRecursive)):
            CleanParentz(item, wlist)

        # Clear the tree and import the codes
        self.TreeWidget.clear()
        self.ParseDatabase(tree.xpath('category') + tree.xpath('code'), None, 3)

        # Overwrite the original file and disable the update button, since we no longer need it.
        shutil.move('tmp.xml', self.dbfile)
        self.UpdateButton.setEnabled(False)

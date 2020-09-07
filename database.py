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

        # Hide header, enable multiple selection, set items as draggable and add some space on the right
        self.TreeWidget.setHeaderHidden(True)
        self.TreeWidget.setSelectionMode(QtWidgets.QTreeWidget.ExtendedSelection)
        self.TreeWidget.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        header = self.TreeWidget.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # Add the search bar
        self.SearchBar = QtWidgets.QLineEdit()
        self.SearchBar.setPlaceholderText('Search codes...')
        self.SearchBar.textEdited.connect(self.HandleSearch)

        # Add the opened codelist combo box...
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')

        # ...and the "Add" button
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

        # Enable the update button if an url is present
        self.UpdateButton.setEnabled(bool(self.updateURL))

        # Import the codes (the second tree is because there can be codes without a category)
        self.ParseDatabase(tree.xpath('category') + tree.xpath('code'), None)

    def ParseDatabase(self, tree: etree, parent: Optional[QtWidgets.QTreeWidgetItem]):
        """
        Recursively create the code tree based on the xml
        """
        for entry in tree:
            newitem = ModdedTreeWidgetItem(entry.attrib['name'], entry.tag == 'category', False)

            # Determine parenthood
            if parent:
                parent.addChild(newitem)
            else:
                self.TreeWidget.addTopLevelItem(newitem)

            # Determine type of entry. Elif makes sure unknown entries are ignored.
            if entry.tag == 'category':
                self.ParseDatabase(entry, newitem)
            elif entry.tag == 'code':
                newitem.setText(1, entry[0].text.strip().upper())
                newitem.setText(2, entry.attrib['comment'])
                newitem.setText(4, entry.attrib['author'])

    def HandleSelection(self):
        """
        Self explanatory.
        """
        SelectItems(self.TreeWidget)
        self.EnableButtons()

    def EnableButtons(self):
        """
        Updates the Add button.
        """
        self.AddButton.setEnabled(bool(list(CountCheckedCodes(self.TreeWidget, False))))

    def HandleSearch(self, text: str):
        """
        Filters codes based on a given string
        """
        for item in self.TreeWidget.findItems('', Qt.MatchContains | Qt.MatchRecursive):
            # Hide all items
            item.setHidden(True)

            # Unhide the item if its name or code match, then unhide its parents
            if item.text(1) and any(text.lower() in item.text(i).lower() for i in range(2)):
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
            win.setWidget(CodeList(''))
            globalstuff.mainWindow.mdi.addSubWindow(win)
            win.widget().AddFromDatabase(enabledlist, self.gameID)
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
            msgbox = QtWidgets.QMessageBox.question(globalstuff.mainWindow, 'Download Error',
                                                    'There was an error during the database download. Retry?')
            if msgbox == QtWidgets.QMessageBox.Yes:
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
            QtWidgets.QMessageBox.information(globalstuff.mainWindow, 'Up to date', 'Database is up to date!')
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
        self.ParseDatabase(tree.xpath('category') + tree.xpath('code'), None)

        # Overwrite the original file and disable the update button, since we no longer need it.
        shutil.move('tmp.xml', self.dbfile)
        self.UpdateButton.setEnabled(False)

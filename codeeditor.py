"""
The CodeEditor is a relatively simple window which shows a code, its name, author and comment. It also lets you edit it
and open it with other windows, or add it to different lists.
"""
import os
import re
from typing import Optional

from PyQt5 import QtGui, QtWidgets
from PyQt5.Qt import Qt

import globalstuff


class CodeEditor(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QTreeWidgetItem], fromdb: bool):
        super().__init__()

        # Initialize vars
        self.parentz = parent  # This is named parentz due to a name conflict
        self.fromdb = fromdb
        name = 'New Code'
        code = comment = author = ''

        if self.parentz:
            name = parent.text(0)
            code = parent.text(1)
            comment = parent.text(2)
            author = parent.text(4)

        # Create the author, code and comment forms
        self.NameLabel = QtWidgets.QLabel('Name:')
        self.CodeName = QtWidgets.QLineEdit(name)
        self.AuthorLabel = QtWidgets.QLabel('Author:')
        self.CodeAuthor = QtWidgets.QLineEdit(author)
        self.CodeLabel = QtWidgets.QLabel('Code:')
        self.CodeContent = QtWidgets.QPlainTextEdit(code)
        self.CommentLabel = QtWidgets.QLabel('Comment:')
        self.CodeComment = QtWidgets.QPlainTextEdit(comment)

        # Use Monospaced font for the code
        self.CodeContent.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))

        # Connect
        self.CodeName.textEdited.connect(self.SetDirty)
        self.CodeAuthor.textEdited.connect(self.SetDirty)
        self.CodeContent.textChanged.connect(self.SetDirty)
        self.CodeComment.textChanged.connect(self.SetDirty)

        # Save button
        self.SaveButton = QtWidgets.QPushButton('Save Changes')
        self.SaveButton.setEnabled(False)
        self.SaveButton.clicked.connect(self.SaveCode)

        # Add the opened codelist combo box
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')

        # Finally, add the "Add" button
        self.AddButton = QtWidgets.QPushButton('Save to Codelist')
        self.AddButton.clicked.connect(lambda: globalstuff.mainWindow.AddFromEditor(self, self.Combox.currentData()))
        if code:
            self.AddButton.setEnabled(False)

        # Set the window title
        if author:
            self.setWindowTitle('Code Editor - {} [{}]'.format(name, author))
        else:
            self.setWindowTitle('Code Editor - {}'.format(name))

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.NameLabel, 0, 0, 1, 2)
        lyt.addWidget(self.CodeName, 1, 0, 1, 2)
        lyt.addWidget(self.AuthorLabel, 2, 0, 1, 2)
        lyt.addWidget(self.CodeAuthor, 3, 0, 1, 2)
        lyt.addWidget(self.CodeLabel, 4, 0, 1, 2)
        lyt.addWidget(self.CodeContent, 5, 0, 1, 2)
        lyt.addWidget(self.CommentLabel, 6, 0, 1, 2)
        lyt.addWidget(self.CodeComment, 7, 0, 1, 2)
        lyt.addWidget(self.SaveButton, 8, 0, 1, 2)
        lyt.addWidget(self.Combox, 9, 0)
        lyt.addWidget(self.AddButton, 9, 1)
        self.setLayout(lyt)

    def SetDirty(self):
        """
        Enables the save button if the code is not empty and the parent is set (otherwise we'd have nowhere to save to)
        """
        if self.CodeContent.toPlainText() and self.CodeName.text():
            if not self.fromdb:
                self.SaveButton.setEnabled(bool(self.parentz))
            self.AddButton.setEnabled(True)
        else:
            self.SaveButton.setEnabled(False)
            self.AddButton.setEnabled(False)

    def SaveCode(self):
        """
        Saves the code to the designated parent.
        """
        # Initialize vars
        code = self.ParseCode()
        comment = re.sub('\n{2,}', '\n', self.CodeComment.toPlainText())
        author = self.CodeAuthor.text()

        # Save the stuff
        self.parentz.setText(0, self.CodeName.text())
        self.parentz.setText(1, code)
        self.parentz.setText(2, comment)
        self.parentz.setText(4, author)

        # Update the fields
        self.CodeContent.setPlainText(code)
        self.CodeComment.setPlainText(comment)

        # Update window title
        self.ParseAuthor(author)

    def ParseCode(self):
        """
        Parses the code to make sure it is formatted properly.
        """
        # Remove spaces and new lines
        code = re.sub('[ \n]', '', self.CodeContent.toPlainText())

        # Add padding if the code is not a multiple of 16
        while len(code) % 16:
            code += '0'

        # Assemble the code and force uppercase
        assembledcode = ''
        for index, char in enumerate(code):
            if not index % 16 and index:
                assembledcode = '\n'.join([assembledcode, char.upper()])
            elif not index % 8 and index:
                assembledcode = ' '.join([assembledcode, char.upper()])
            else:
                assembledcode = ''.join([assembledcode, char.upper()])
        return assembledcode

    def ParseAuthor(self, author):
        """
        Because we really don't like duplication.
        """
        # Update the window title
        if author:
            self.setWindowTitle('Code Editor - {} [{}]'.format(self.name, author))
        else:
            self.setWindowTitle('Code Editor - {}'.format(self.name))

        # Disable the save button
        self.SaveButton.setEnabled(False)


def HandleCodeOpen(item: QtWidgets.QTreeWidgetItem, fromdb: bool):
    """
    Opens a tree's currently selected code in a CodeEditor window.
    """
    if item.text(1):
        willcreate = True
        for window in globalstuff.mainWindow.mdi.subWindowList():  # Find if there's an existing CodeEditor with same parent and window title
            if isinstance(window.widget(), CodeEditor) and window.widget().parentz == item:
                willcreate = False
                globalstuff.mainWindow.mdi.setActiveSubWindow(window)  # This code was already opened, so let's just set the focus on the existing window
                break
        if willcreate:  # If the code is not already open, go ahead and do it
            HandleAddCode(item, fromdb)


def HandleAddCode(item: Optional[QtWidgets.QTreeWidgetItem], fromdb: bool):
    """
    Opens an empty CodeEditor sub-window.
    """
    win = QtWidgets.QMdiSubWindow()
    win.setWidget(CodeEditor(item, fromdb))
    win.setAttribute(Qt.WA_DeleteOnClose)
    globalstuff.mainWindow.mdi.addSubWindow(win)
    globalstuff.mainWindow.updateboxes()
    win.show()


def CleanParentz(item: QtWidgets.QTreeWidgetItem, wlist: list):
    """
    Unsets the parentz parameter for the removed tree item.
    """
    for window in wlist:
        if window.parentz == item:
            window.parentz = None
            break


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
    for window in globalstuff.mainWindow.mdi.subWindowList():
        if isinstance(window.widget(), CodeEditor) and window.widget().parentz == item:
            window.widget().CodeName.setText(item.text(0))
            if item.text(4):
                window.widget().setWindowTitle('Code Editor - {} [{}]'.format(item.text(0), item.text(4)))
            else:
                window.widget().setWindowTitle('Code Editor - {}'.format(item.text(0)))
            return

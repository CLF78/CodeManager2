"""
The CodeEditor is a relatively simple window which shows a code, its name, author and comment. It also lets you edit it
and open it with other windows, or add it to different lists.
"""
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff


class CodeEditor(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__()

        # Initialize vars
        self.parentz = parent  # This is named parentz due to a name conflict
        self.name = 'New Code'
        self.code = self.comment = self.placeholders = self.author = ''

        if self.parentz:
            self.name = parent.text(0)
            self.code = parent.text(1)
            self.comment = parent.text(2)
            self.placeholders = parent.text(3)
            self.author = parent.text(4)

        # Create the author, code and comment forms
        self.AuthorLabel = QtWidgets.QLabel('Author:')
        self.CodeAuthor = QtWidgets.QLineEdit(self.author)
        self.CodeLabel = QtWidgets.QLabel('Code:')
        self.CodeContent = QtWidgets.QPlainTextEdit(self.code)
        self.CommentLabel = QtWidgets.QLabel('Comment:')
        self.CodeComment = QtWidgets.QPlainTextEdit(self.comment)

        # Save button
        self.SaveButton = QtWidgets.QPushButton('Save Changes')
        self.SaveButton.setEnabled(False)

        # Add the opened codelist combo box
        self.Combox = QtWidgets.QComboBox()
        self.Combox.addItem('Create New Codelist')

        # Finally, add the "Add" button
        self.AddButton = QtWidgets.QPushButton('Add to Codelist')

        # Set the window title
        if self.author:
            self.setWindowTitle('Code Editor - {} [{}]'.format(self.name, self.author))
        else:
            self.setWindowTitle('Code Editor - {}'.format(self.name))

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.AuthorLabel, 0, 0, 1, 2)
        lyt.addWidget(self.CodeAuthor, 1, 0, 1, 2)
        lyt.addWidget(self.CodeLabel, 2, 0, 1, 2)
        lyt.addWidget(self.CodeContent, 3, 0, 1, 2)
        lyt.addWidget(self.CommentLabel, 4, 0, 1, 2)
        lyt.addWidget(self.CodeComment, 5, 0, 1, 2)
        lyt.addWidget(self.SaveButton, 6, 0, 1, 2)
        lyt.addWidget(self.Combox, 7, 0)
        lyt.addWidget(self.AddButton, 7, 1)
        self.setLayout(lyt)


def HandleCodeOpen(item: QtWidgets.QTreeWidgetItem):
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
            HandleAddCode(item)


def HandleAddCode(item: Optional[QtWidgets.QTreeWidgetItem]):
    """
    Opens an empty CodeEditor sub-window.
    """
    win = QtWidgets.QMdiSubWindow()
    win.setWidget(CodeEditor(item))
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
        if isinstance(window.widget(), CodeEditor) and window.widget.parentz == item:
            if item.text(4):
                window.widget().setWindowTitle('Code Editor - {} [{}]'.format(item.text(0), item.text(4)))
            else:
                window.widget().setWindowTitle('Code Editor - {}'.format(item.text(0)))
            return

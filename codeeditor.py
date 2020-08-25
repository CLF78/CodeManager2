"""
The CodeEditor is a relatively simple window which shows a code, its name, author and comment. It also lets you edit it
and open it with other windows, or add it to different lists.
"""
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

        # Create the code and comment forms and set the window title
        self.CodeContent = QtWidgets.QPlainTextEdit(self.code)
        self.CodeComment = QtWidgets.QPlainTextEdit(self.comment)
        if self.author:
            self.setWindowTitle('Code Editor - {} [{}]'.format(self.name, self.author))
        else:
            self.setWindowTitle('Code Editor - {}'.format(self.name))

        # Make a layout and set it
        lyt = QtWidgets.QGridLayout()
        lyt.addWidget(self.CodeContent, 0, 0)
        lyt.addWidget(self.CodeComment, 1, 0)
        self.setLayout(lyt)


def HandleCodeOpen(item):
    """
    Opens a tree's currently selected code in a CodeEditor window.
    """
    if item and item.text(1):
        willcreate = True
        for window in globalstuff.mainWindow.mdi.subWindowList():  # Find if there's an existing CodeEditor with same parent and window title
            if isinstance(window.widget(), CodeEditor) and window.widget().parentz == item:
                willcreate = False
                globalstuff.mainWindow.mdi.setActiveSubWindow(window)  # This code was already opened, so let's just set the focus on the existing window
                break
        if willcreate:  # If the code is not already open, go ahead and do it
            HandleAddCode(item)


def HandleAddCode(item):
    """
    Opens an empty CodeEditor sub-window.
    """
    win = QtWidgets.QMdiSubWindow()
    win.setWidget(CodeEditor(item))
    win.setAttribute(Qt.WA_DeleteOnClose)
    globalstuff.mainWindow.mdi.addSubWindow(win)
    win.show()

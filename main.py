"""
Main executable, unsurprisingly. Also known as the circular import prevention junkyard.
"""
import os
import re
import sys
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import exporting
import importing
import globalstuff
from codeeditor import CodeEditor
from codelist import CodeList
from database import Database
from titles import DownloadError
from widgets import ModdedSubWindow, ModdedTreeWidgetItem


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Create the interface
        self.mdi = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi)

        # Create the menubar
        self.optgct = self.optini = self.opttxt = None
        self.createMenubar()

        # Set window title and show the window maximized
        self.setWindowTitle('Code Manager Reborn')
        self.showMaximized()

        # Check for the wiitdb.txt file
        if not os.path.isfile(globalstuff.wiitdb):
            DownloadError()

    def createMenubar(self):
        """
        Sets up the menubar
        """
        bar = self.menuBar()

        # File Menu
        file = bar.addMenu('File')
        file.addAction('Exit', self.close)

        # Import menu
        imports = bar.addMenu('Import')
        imports.addAction('Import Database', self.openDatabase)
        imports.addAction('Import Codelist', lambda: self.openCodelist(None))

        # Export menu
        exports = bar.addMenu('Export')
        exportopts = exports.addMenu('Export All Lists To')
        self.optgct = exportopts.addAction('GCT', lambda: self.exportMultiple('gct'))
        self.opttxt = exportopts.addAction('TXT', lambda: self.exportMultiple('txt'))
        self.optini = exportopts.addAction('INI', lambda: self.exportMultiple('ini'))

        # Update the menu
        self.updateboxes()

    def openDatabase(self):
        """
        Opens a dialog to let the user choose a database.
        """
        name = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Database', '', 'Code Database (*.xml)')[0]
        if name:
            win = QtWidgets.QMdiSubWindow()
            win.setWidget(Database(name))
            win.setAttribute(Qt.WA_DeleteOnClose)
            self.mdi.addSubWindow(win)
            self.updateboxes()
            win.show()

    def openCodelist(self, source: Optional[QtWidgets.QTreeWidget]):
        """
        Opens a QFileDialog to import a file
        """
        files = QtWidgets.QFileDialog.getOpenFileNames(self, 'Open Files', '',
                                                       'All supported formats (*.txt *.ini *.gct *.dol);;'
                                                       'Text File (*.txt);;'
                                                       'Dolphin INI (*.ini);;'
                                                       'Gecko Code Table (*.gct);;'
                                                       'Dolphin Executable (*.dol)')[0]

        # Run the correct function based on the chosen format
        for file in files:
            func = getattr(importing, 'Import' + os.path.splitext(file)[1].lstrip('.').upper(), None)
            if func:
                func(file, source)

    def exportList(self, source: QtWidgets.QTreeWidget):
        """
        Opens a QFileDialog to save a single codelist to a file.
        """
        file = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Codelist To', source.gameID,
                                                     'Gecko Code Table (*.gct);;'
                                                     'Text File (*.txt);;'
                                                     'Dolphin INI (*.ini);;')[0]

        # Run the correct function based on the chosen format
        func = getattr(exporting, 'Export' + os.path.splitext(file)[1].lstrip('.').upper(), None)
        if func:
            success = func(file, source, False)

            # Inform the user
            if success:
                msgbox = QtWidgets.QMessageBox()
                msgbox.setWindowTitle('Export Complete!')
                msgbox.setText('List exported successfully!')
                msgbox.exec_()

    def exportMultiple(self, ext: str):
        """
        Exports all the currently opened codelists at once to the given format. Filename defaults to the game id.
        """
        # Get destination and codelists
        dest = QtWidgets.QFileDialog.getExistingDirectory(self, 'Save all Codelists to', '', QtWidgets.QFileDialog.ShowDirsOnly)
        success = total = 0

        # Do the thing
        for window in filter(lambda x: isinstance(x.widget(), CodeList), self.mdi.subWindowList()):

            # Initialize vars
            filename = os.path.join(dest, '.'.join([window.widget().gameID, ext]))
            i = 2

            # Check that the file doesn't exist, if so bump up the number
            while os.path.isfile(filename):
                filename = os.path.join(dest, '{}_{}.{}'.format(window.widget().gameID, i, ext))
                i += 1

            # Choose the correct function based on the provided extension
            func = getattr(exporting, 'Export' + ext.upper(), None)
            if func:
                success += func(filename, window.widget(), True)
            total += 1

        # Inform the user
        if success:
            msgbox = QtWidgets.QMessageBox()
            msgbox.setWindowTitle('Export Complete!')
            msgbox.setText('{}/{} lists exported successfully!'.format(success, total))
            msgbox.exec_()

    def updateboxes(self):
        """
        Looks for opened codelist sub-windows and adds them to each database' combo box.
        """
        # Initialize vars
        dblist = []
        entries = []

        # Fill the two lists
        for window in self.mdi.subWindowList():
            if isinstance(window.widget(), CodeList):
                entries.append(window.widget())
            else:
                dblist.append(window.widget())

        # Update the "Export All" option
        notempty = bool(entries)
        self.optgct.setEnabled(notempty)
        self.opttxt.setEnabled(notempty)
        self.optini.setEnabled(notempty)

        # Begin updating each combo box
        for window in dblist:

            # Process the combo box in reverse, so we can safely delete items without worrying about wrong indexes
            for i in reversed(range(1, window.Combox.count())):
                item = window.Combox.itemData(i)
                if item.parentWidget() not in self.mdi.subWindowList():
                    window.Combox.removeItem(i)
                else:
                    entries.remove(item)

            # Add the remaining windows if they meet the condition
            for entry in entries:
                window.Combox.addItem(entry.windowTitle()[11:], entry)  # Only keep game name and id

    def CodeLookup(self, item: QtWidgets.QTreeWidgetItem, codelist: QtWidgets.QTreeWidget, gid: str):
        """
        Looks for a possible match in opened windows with the same game id.
        """
        # Initialize vars
        wlist = [w.widget() for w in self.mdi.subWindowList() if isinstance(w.widget(), Database)
                 or isinstance(w.widget(), CodeList) and w.widget().TreeWidget is not codelist]
        lsplt = re.split('[ \n]', item.text(1))
        totalen = len(lsplt)

        # Begin search!
        for widget in wlist:

            # Mark code matches from different regions with an additional asterisk
            regmatch = not(bool(widget.gameID == gid)) + 1

            # Process the widget's tree
            for child in filter(lambda x: x.text(1), widget.TreeWidget.findItems('', Qt.MatchContains | Qt.MatchRecursive)):
                matches = 0

                # For each code, check each line of the code we're looking a name for
                for line in lsplt:
                    if line in child.text(1):
                        matches += 1

                    # If more than 2/3rds of the code match, we found the code we were looking for
                    if matches / totalen >= 2 / 3:
                        item.setText(0, child.text(0) + '*' * regmatch)
                        item.setText(2, child.text(2))  # Copy comment
                        item.setText(4, child.text(4))  # Copy author
                        return

    def AddFromEditor(self, src: CodeEditor, dest: CodeList):
        """
        Transfers the code editor's content to a code in a codelist. If you're wondering why this is here, it's to
        prevent circular imports. Fuck circular imports.
        """
        # Initialize vars
        code = src.ParseCode()
        comment = re.sub('\n{2,}', '\n', src.CodeComment.toPlainText())
        author = src.CodeAuthor.text()

        # Create a new codelist if dest is None
        if not dest:
            dest = CodeList('')
            win = ModdedSubWindow()
            win.setWidget(dest)
            self.mdi.addSubWindow(win)
            self.updateboxes()
            win.show()

        # Save the stuff
        newitem = ModdedTreeWidgetItem(src, False, True)
        newitem.setText(1, code)
        newitem.setText(2, comment)
        newitem.setText(4, author)

        # Update the fields
        src.CodeContent.setPlainText(code)
        src.CodeComment.setPlainText(comment)

        # Update window title
        src.ParseAuthor(author)

        # Add the item to the widget
        dest.TreeWidget.addTopLevelItem(newitem)


def main():
    # Start the application
    app = QtWidgets.QApplication(sys.argv)
    globalstuff.mainWindow = MainWindow()
    ret = app.exec_()

    # Quit the process
    sys.exit(ret)


if __name__ == '__main__':
    main()

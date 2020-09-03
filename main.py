import os
import re
import sys
from typing import Optional

from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from database import Database
from importing import ImportTXT, ImportINI, ImportGCT, ImportDOL
from exporting import ExportTXT, ExportINI, ExportGCT
from titles import DownloadError


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
        file = bar.addMenu('&File')
        file.addAction('Exit', self.close)

        # Import menu
        imports = bar.addMenu('&Import')
        imports.addAction('Import Database', self.openDatabase)
        imports.addAction('Import Codelist', lambda: self.openCodelist(None))

        # Export menu
        exports = bar.addMenu('&Export')
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
        for file in files:
            if '.txt' in file:
                ImportTXT(file, source)
            elif '.ini' in file:
                ImportINI(file, source)
            elif '.gct' in file:
                ImportGCT(file, source)
            elif '.dol' in file:
                ImportDOL(file, source)

    def exportList(self, source: QtWidgets.QTreeWidget):
        """
        Opens a QFileDialog to save a single codelist to a file.
        """
        success = False
        file = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Codelist To', source.gameID,
                                                     'Gecko Code Table (*.gct);;'
                                                     'Text File (*.txt);;'
                                                     'Dolphin INI (*.ini);;')[0]
        if '.txt' in file:
            success = ExportTXT(file, source, False)
        elif '.ini' in file:
            success = ExportINI(file, source, False)
        elif '.gct' in file:
            success = ExportGCT(file, source, False)

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
        entries = [window.widget() for window in self.mdi.subWindowList() if isinstance(window.widget(), CodeList)]
        success = 0

        # Do the thing
        for entry in entries:

            # Initialize vars
            filename = os.path.join(dest, '.'.join([entry.gameID, ext]))
            i = 2

            # Check that the file doesn't exist, if so bump up the number
            while os.path.isfile(filename):
                filename = os.path.join(dest, '{}_{}.{}'.format(entry.gameID, i, ext))
                i += 1

            # Choose the correct function based on the provided extension
            if ext == 'gct':
                success += ExportGCT(filename, entry, True)
            elif ext == 'txt':
                success += ExportTXT(filename, entry, True)
            elif ext == 'ini':
                success += ExportINI(filename, entry, True)

        # Inform the user
        msgbox = QtWidgets.QMessageBox()
        msgbox.setWindowTitle('Export Complete!')
        msgbox.setText('{}/{} lists exported successfully!'.format(success, len(entries)))
        msgbox.exec_()

    def updateboxes(self):
        """
        Looks for opened codelist sub-windows and adds them to each database' combo box.
        """
        dblist = [window.widget() for window in self.mdi.subWindowList() if isinstance(window.widget(), Database)]
        entries = [window.widget() for window in self.mdi.subWindowList() if isinstance(window.widget(), CodeList)]
        for database in dblist:
            if database.Combox.count() - 1 != len(entries):
                database.Combox.clear()
                database.Combox.addItem('Create New Codelist')
                for entry in entries:
                    database.Combox.addItem(entry.windowTitle()[11:], entry)  # Only keep game name and id

        notempty = bool(entries)
        self.optgct.setEnabled(notempty)
        self.opttxt.setEnabled(notempty)
        self.optini.setEnabled(notempty)

    def CodeLookup(self, item: QtWidgets.QTreeWidgetItem, codelist: QtWidgets.QTreeWidget, gid: str):
        """
        Looks for a possible match in opened windows with the same game id.
        """
        # Build window list
        wlist = [window.widget().DBrowser for window in self.mdi.subWindowList() if isinstance(window.widget(), Database) and window.widget().gameID == gid]
        wlist.extend([window.widget().Codelist for window in self.mdi.subWindowList() if isinstance(window.widget(), CodeList) and window.widget().Codelist is not codelist and window.widget().gameID == gid])

        # Initialize vars
        lsplt = re.split('[ \n]', item.text(1))
        totalen = len(lsplt)

        # Begin search! If a code matches by more than 66%, it will be counted as a full match.
        for widget in wlist:
            for child in widget.findItems('', Qt.MatchContains | Qt.MatchRecursive):
                txt = child.text(1)
                if txt:
                    matches = 0
                    for line in lsplt:
                        if line in txt:
                            matches += 1
                        if matches / totalen >= 2 / 3:
                            item.setText(0, child.text(0) + '*')
                            item.setText(2, child.text(2))  # Copy comment
                            item.setText(4, child.text(4))  # Copy author
                            return


def main():
    # Start the application
    app = QtWidgets.QApplication(sys.argv)
    globalstuff.mainWindow = MainWindow()
    ret = app.exec_()

    # Quit the process
    sys.exit(ret)


if __name__ == '__main__':
    main()

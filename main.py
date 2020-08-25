import re
import sys

from PyQt5 import QtWidgets
from PyQt5.Qt import Qt

import globalstuff
from codelist import CodeList
from database import Database
from importing import ImportTXT, ImportINI, ImportGCT, ImportDOL


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # Create the interface
        self.mdi = QtWidgets.QMdiArea()
        self.setCentralWidget(self.mdi)

        # Create the menubar
        self.createMenubar()

        # Set window title and show the window maximized
        self.setWindowTitle('Code Manager 2')
        self.showMaximized()

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

    def openCodelist(self, source):
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

    def updateboxes(self):
        """
        Looks for opened codelist sub-windows and adds them to each database' combo box. Yes PyCharm, i know it is a
        static method but no, i'm not gonna move it out of this class, so deal with it.
        """
        dblist = [window.widget() for window in globalstuff.mainWindow.mdi.subWindowList() if isinstance(window.widget(), Database)]
        entries = [window.windowTitle() for window in globalstuff.mainWindow.mdi.subWindowList() if isinstance(window.widget(), CodeList)]
        for database in dblist:
            if database.Combox.count() - 1 != len(entries):
                database.Combox.clear()
                database.Combox.addItem('Create New Codelist')
                database.Combox.addItems(entries)

    def CodeLookup(self, item, codelist, gid):
        """
        Looks for a possible match in opened windows with the same game id.
        """
        # Build window list
        wlist = [window.widget().DBrowser for window in self.mdi.subWindowList() if isinstance(window.widget(), Database) and window.widget().gameID == gid] + \
                [window.widget().Codelist for window in self.mdi.subWindowList() if isinstance(window.widget(), CodeList) and window.widget().Codelist is not codelist and window.widget().gidInput.text() == gid]

        # Initialize vars
        lsplt = re.split(' |\n', item.text(1))
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

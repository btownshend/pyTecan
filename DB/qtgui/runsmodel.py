from PyQt5 import QtCore
from PyQt5 import QtSql
from PyQt5 import Qt
import sys

class RunsModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.datatable = []
        self.header=[]

    def update(self):
        q=QtSql.QSqlQuery("SELECT r.run, expt, right(r.run,4) runid, program, logfile, starttime, endtime from runs r order by starttime desc")
        if q.lastError().isValid():
            print("SQL error: ",q.lastError().text())
            sys.exit(1)
        self.datatable=[]
        while (q.next()):
            self.datatable.append([q.value(0),q.value(1),q.value(2),q.value(3),q.value(4),q.value(5),q.value(6)])
        print("Retrieved %d runs"%len(self.datatable))
        self.header=['run','expt','runid','program','logfile','starttime','endtime']

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self.datatable)

    def columnCount(self, parent=QtCore.QModelIndex()):
        if len(self.datatable)>0:
            return len(self.datatable[0])
        return 0

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            i = index.row()
            j = index.column()
            return QtCore.QVariant(self.datatable[i][j])
        else:
            return QtCore.QVariant()

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        #print("section=",section,"orientation=",orientation)
        if role== QtCore.Qt.DisplayRole and orientation==Qt.Qt.Horizontal:
            return QtCore.QVariant(self.header[section])
        else:
            return QtCore.QVariant()


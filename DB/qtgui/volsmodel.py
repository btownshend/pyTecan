from PyQt5 import QtCore

class VolsModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.datatable = None

    def update(self, db, run, plate, sample):
        print 'Updating Model'
        self.datatable = dataIn
        print 'Datatable : {0}'.format(self.datatable)

    def rowCount(self, **kwargs):
        return len(self.datatable.index)

    def columnCount(self, **kwargs):
        return len(self.datatable.columns.values)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            i = index.row()
            j = index.column()
            return '{0}'.format(self.datatable.iget_value(i, j))
        else:
            return QtCore.QVariant()

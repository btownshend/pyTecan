import sys

from PyQt5 import QtSql
from PyQt5.QtCore import QTimeZone, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem

from gui_auto import Ui_MainWindow


class GUI(Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.currentRun = None
        self.currentPlate = None
        self.currentWell = None
        self.currentSample = None

    def dbopen(self):
        self.db = QtSql.QSqlDatabase.addDatabase('QMYSQL')
        self.db.setHostName("35.203.151.202")
        self.db.setUserName("robot")
        self.db.setPassword("cdsrobot")  # correct password here
        self.db.setDatabaseName("robot")
        print("options=",self.db.connectOptions())
        self.db.open()
        settz=QtSql.QSqlQuery()
        settz.exec("set time_zone='US/Pacific'")
        
    def setupUi(self,mainWindow):
        super().setupUi(mainWindow)
        self.refresh.clicked.connect(ui.refreshAll)
        self.actionQuit.triggered.connect(ui.quit)
        self.actionRuns.triggered.connect(ui.runs)
        self.runsTable.clicked.connect(ui.selectRun)
        self.plateTable.clicked.connect(ui.selectPlate)
        self.sampleTable.clicked.connect(ui.selectSample)

        self.pgmvolsTable.hide()
        self.dbopen()
        self.refreshAll(False)
        print("timezone=",QTimeZone.systemTimeZone().comment())

    def sqlErrorCheck(self,lastError):
        if lastError.isValid():
            print("SQL error: ",lastError.type(),lastError.text())
            sys.exit(1)

    def refreshRunsTable(self):
        q=QtSql.QSqlQueryModel()
        q.setQuery("SELECT r.run, right(r.run,4) runid, program, gentime, starttime, endtime, if(endtime is null,round(min(remaining)),'')  remtime from runs r, ticks t where r.run=t.run group by r.run order by starttime desc")
        self.sqlErrorCheck(q.lastError())
        self.runsTable.setModel(q)
        self.runsTable.setColumnHidden(0,True)
        self.runsTable.resizeColumnsToContents()

    def refreshPgmVolsTable(self):
        q=QtSql.QSqlQueryModel()
        q.setQuery("select s.program,s.name,s.plate,s.well,o.elapsed,o.tip,o.volchange,o.volume from pgm_ops o, pgm_samples s where o.pgm_sample=s.pgm_sample order by s.plate,s.well,o.pgm_op")
        self.sqlErrorCheck(q.lastError())
        self.pgmvolsTable.setModel(q)
        self.pgmvolsTable.resizeColumnsToContents()

    def refreshRunGroup(self):
        print("refreshRunsGroup: run=",self.currentRun)
        if self.currentRun is None:
            self.runGroup.hide()
            self.currentPlate=None
            return
        self.runGroup.show()
        self.refreshRunsDetail()
        self.refreshPlatesTable()
        self.refreshPlateGroup()

    def refreshRunsDetail(self):
        q=QtSql.QSqlQuery("SELECT program, date_format(gentime,'%%m/%%d/%%y %%H:%%i'), date_format(starttime,'%%m/%%d/%%y %%H:%%i'), date_format(endtime,'%%m/%%d/%%y %%H:%%i'), if(endtime is null,round(min(remaining)),'')  remtime from runs r, ticks t where r.run='%s' and r.run=t.run group by r.run order by starttime desc"%self.currentRun)
        self.sqlErrorCheck(q.lastError())
        q.next()
        self.programName.setText(q.value(0))
        print("q.value(1)=",q.value(1))
        self.generated.setText("Gen: "+q.value(1))
        self.starttime.setText("Start: "+q.value(2))
        print("q.value(3)=",q.value(3))
        if q.value(3) is None:
            self.endtime.setText("Rem: "+q.value(4)+" min")
        else:
            self.endtime.setText("End: "+q.value(3))

    def refreshPlatesTable(self):
        q=QtSql.QSqlQueryModel()
        query="SELECT plate,count(*) numsamps from sampnames s where s.run='%s' group by plate order by plate"%self.currentRun
        print(query)
        q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.plateTable.setModel(q)
        self.plateTable.resizeColumnsToContents()

    def refreshSamplesTable(self):
        q=QtSql.QSqlQueryModel()
        query = "select s.well,s.name,v.volume,v.expected,v.measured,v.vol from sampnames s, vols v where v.vol=(select max(vol) from vols vm where vm.run=s.run and vm.plate=s.plate and vm.well=s.well) and s.plate='%s' and s.run='%s' order by right(s.well,length(s.well)-1),s.well;" % (
        self.currentPlate, self.currentRun)
        print(query)
        q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.sampleTable.setModel(q)
        self.sampleTable.resizeColumnsToContents()

    def refreshSampleDetail(self):
        pass

    def refreshVolsTable(self):
        q=QtSql.QSqlQueryModel()
        q.setQuery("select gemvolume,volume,expected,measured from vols v where v.plate='%s' and v.well='%s' and v.run='%s' order by v.vol;"%(self.currentPlate,self.currentWell,self.currentRun))
        self.sqlErrorCheck(q.lastError())
        self.volsTable.setModel(q)
        self.volsTable.resizeColumnsToContents()

    def refreshPlateGroup(self):
        print("refreshPlateGroup: plate=",self.currentPlate)
        if self.currentPlate is None:
            self.plateGroup.hide()
            self.currentWell=None
            return
        self.plateGroup.show()
        self.plateName.setText(self.currentPlate)
        self.refreshSamplesTable()
        self.refreshSampleGroup()

    def refreshSampleGroup(self):
        print("refreshSampleGroup: sample=", self.currentWell)
        if self.currentWell is None:
            self.sampleGroup.hide()
            return
        self.sampleGroup.show()
        self.refreshSampleDetail()
        self.sampleName.setText(self.currentSample)
        self.wellName.setText(self.currentPlate+"."+self.currentWell)
        self.refreshVolsTable()

    def refreshAll(self,arg):
        print("refresh",arg)
        self.refreshRunsTable()
        #self.refreshPgmVolsTable()
        self.refreshRunGroup()
        self.refreshPlateGroup()
        self.refreshSampleGroup()

    def runs(self,arg):
        print("runs",arg)

    def selectRun(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        rec=self.runsTable.model().record(index.row())
        for i in range(rec.count()):
            print(rec.fieldName(i),"=",rec.field(i).value())
        self.currentRun=rec.field(0).value()
        #self.runsTable.selectRow(index.row())
        self.refreshRunGroup()

    def selectPlate(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        rec=self.plateTable.model().record(index.row())
        for i in range(rec.count()):
            print(rec.fieldName(i),"=",rec.field(i).value())
        self.currentPlate=rec.field(0).value()
        #self.plateTable.selectRow(index.row())
        self.refreshPlateGroup()

    def selectSample(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        rec=self.sampleTable.model().record(index.row())
        for i in range(rec.count()):
            print(rec.fieldName(i),"=",rec.field(i).value())
        self.currentWell=rec.field(0).value()
        self.currentSample=rec.field(1).value()
        #self.plateTable.selectRow(index.row())
        self.refreshSampleGroup()

    def quit(self):
        print("quit")
        sys.exit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = GUI()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
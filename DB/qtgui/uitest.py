import sys

from PyQt5 import QtSql
from PyQt5.QtCore import QTimeZone, QModelIndex
from PyQt5.QtWidgets import QApplication, QMainWindow

from gui_auto import Ui_MainWindow


class GUI(Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.currentRun = None
        self.currentPlate = None
        self.currentWell = None
        self.currentSample = None
        self.currentProgram = None
        self.db = None

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
        self.dbopen()
        self.refreshAll()
        print("timezone=",QTimeZone.systemTimeZone().comment())

    def sqlErrorCheck(self,lastError):
        if lastError.isValid():
            print("SQL error: ",lastError.type(),lastError.text())
            sys.exit(1)

    def refreshRunsTable(self):
        q=QtSql.QSqlQueryModel()
        q.setQuery("SELECT r.run, right(r.run,4) runid, program, logfile, starttime, endtime from runs r order by starttime desc")
        self.sqlErrorCheck(q.lastError())
        self.runsTable.setModel(q)
        self.runsTable.setColumnHidden(0,True)
        self.runsTable.resizeColumnsToContents()

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
        q=QtSql.QSqlQuery("SELECT p.name, date_format(gentime,'%%m/%%d/%%y %%H:%%i'), date_format(starttime,'%%m/%%d/%%y %%H:%%i'), date_format(endtime,'%%m/%%d/%%y %%H:%%i'),r.logfile from runs r, programs p where r.program=p.program and r.run='%s' group by r.run order by starttime desc"%self.currentRun)
        self.sqlErrorCheck(q.lastError())
        if not q.next():
            self.currentRun=None
            return
        self.programName.setText(q.value(0))
        print("q.value(1)=",q.value(1))
        self.generated.setText("Gen: "+q.value(1))
        self.starttime.setText("Start: "+q.value(2))
        self.logFile.setText(q.value(4))
        print("q.value(3)=",q.value(3))
        if q.value(3) is not None:
            self.endtime.setText("End: "+q.value(3))

    def refreshPlatesTable(self):
        q=QtSql.QSqlQueryModel()
        query="SELECT plate,count(*) numsamps from samples s where s.program=(select program from runs where run='%s') group by plate order by plate"%self.currentRun
        print(query)
        q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.plateTable.setModel(q)
        self.plateTable.resizeColumnsToContents()

    def refreshSamplesTable(self):
        q=QtSql.QSqlQueryModel()
        query = "select s.sample,s.well,s.name  from samples s where s.plate='%s' and s.program=%d order by right(s.well,length(s.well)-1),s.well;" % (self.currentPlate, self.currentProgram)
        print(query)
        q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.sampleTable.setModel(q)
        self.sampleTable.setColumnHidden(0,True)
        self.sampleTable.resizeColumnsToContents()

    def refreshSampleDetail(self):
        print("currentSample=",self.currentSample)
        query = "SELECT name,plate,well FROM samples WHERE sample=%d" % self.currentSample
        print(query)
        q=QtSql.QSqlQuery(query)
        self.sqlErrorCheck(q.lastError())
        q.next()
        self.sampleName.setText(q.value(0))
        self.wellName.setText(q.value(1)+"."+q.value(2))

    def refreshVolsTable(self):
        q=QtSql.QSqlQueryModel()
        query="select lineno,round(elapsed/60.0,1) elapsed,cmd,tip,round(estvol,1) estvol, round(volume,1) observed,measured,round(volchange,1) volchange from v_history where run='%s' and sample=%d order by lineno;"%(self.currentRun, self.currentSample)
        print(query)
        q.setQuery(query)
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
        self.refreshVolsTable()
        self.sampleGroup.layout()

    def refreshAll(self):
        self.refreshRunsTable()
        self.refreshRunGroup()
        self.refreshPlateGroup()
        self.refreshSampleGroup()
        self.central.layout()

    def runs(self,arg):
        print("runs",arg)

    def selectRun(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        rec=self.runsTable.model().record(index.row())
        for i in range(rec.count()):
            print(rec.fieldName(i),"=",rec.field(i).value())
        self.currentRun=rec.field(0).value()
        self.currentProgram=rec.field(2).value()
        self.currentPlate=None
        self.currentSample=None
        self.currentWell=None
        #self.runsTable.selectRow(index.row())
        self.refreshAll()

    def selectPlate(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        rec=self.plateTable.model().record(index.row())
        for i in range(rec.count()):
            print(rec.fieldName(i),"=",rec.field(i).value())
        self.currentPlate=rec.field(0).value()
        #self.plateTable.selectRow(index.row())
        self.currentSample=None
        self.currentWell=None
        self.refreshAll()

    def selectSample(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        rec=self.sampleTable.model().record(index.row())
        for i in range(rec.count()):
            print(rec.fieldName(i),"=",rec.field(i).value())
        self.currentWell=rec.field(0).value()
        self.currentSample=rec.field(0).value()
        #self.plateTable.selectRow(index.row())
        self.refreshAll()

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
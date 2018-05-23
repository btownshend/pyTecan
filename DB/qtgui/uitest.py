import sys

from PyQt5 import QtSql
from PyQt5.QtCore import QTimeZone, QModelIndex, QDateTime
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem
from PyQt5.Qt import QColor

from gui_auto import Ui_MainWindow
from runsmodel import RunsModel

class GUI(Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.currentRun = None
        self.currentProgram = None
        self.currentPlate = None
        self.currentWell = None
        self.currentSample = None
        self.currentProgram = None
        self.currentVolume = None
        self.sampInfo = {}
        self.lastMeasured=None
        self.lastElapsed=0
        self.endElapsed=None
        self.endTime=None

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

    def dbcheck(self):
        """Check if DB connection is OK"""
        if not self.db.isValid():
            self.dbopen()

    def dbreopen(self):
        if self.db.isValid():
            self.db.close()
        self.dbopen()

    def dbget(self,query):
        print("dbget(",query,")")
        q=QtSql.QSqlQuery(query)
        if q.lastError().isValid():
            self.dbreopen()
            q = QtSql.QSqlQuery(query)
        self.sqlErrorCheck(q.lastError())
        valid=q.next()
        return q if valid else None

    def setupUi(self,mainWindow):
        super().setupUi(mainWindow)
        self.refresh.clicked.connect(ui.refreshAll)
        self.actionQuit.triggered.connect(ui.quit)
        #self.actionRuns.triggered.connect(ui.runs)
        self.runsTable.clicked.connect(ui.selectRun)
        self.plateTable.clicked.connect(ui.selectPlate)
        self.sampleTable.clicked.connect(ui.selectSample)
        self.dbopen()
        self.refreshAll()
        print("timezone=",QTimeZone.systemTimeZone().comment())

    def sqlErrorCheck(self,lastError):
        if lastError.isValid():
            print("SQL error: ",lastError.type(),lastError.text())
            import pdb
            pdb.set_trace()
            sys.exit(1)

    def getSampData(self,sampid,horizon):
        """Get Sample info for given sampid for horizon hours"""
        print("getSampData(%d,%f)"%(sampid,horizon))
        if sampid not in self.sampInfo:
            q=self.dbget("""
                SELECT v.op,estvol,volume,volchange,elapsed+timestampdiff(second,measured,now()) elapsed
                FROM vols v, ops o
                WHERE sample=%d
                AND v.op=o.op
                AND run=%d
                ORDER BY v.op DESC
                LIMIT 1
            """%(sampid,self.currentRun))
            if q!=None:
                print(q.value(0),q.value(1),"Null" if q.isNull(2) else q.value(2),q.value(3),q.value(4))
                lastop=q.value(0)
                if q.isNull(2):
                    estvol=q.value(1)+q.value(3)
                else:
                    estvol=q.value(2)+q.value(3)
                elapsed=q.value(4)
            else:
                lastop=0
                estvol=0
                elapsed=0
            q2=self.dbget("""
                SELECT sum(volchange) futurevols
                FROM ops
                WHERE op>%d
                AND sample=%d
                AND program=%d
                """%(lastop,sampid,self.currentProgram))
            finalvol=q2.value(0)+estvol
            q3=self.dbget("""
                SELECT sum(volchange) futurevols
                FROM ops
                WHERE op>%d
                AND sample=%d
                AND program=%d
                AND elapsed<=%f
                """%(lastop,sampid,self.currentProgram,elapsed+horizon*3600))   # TODO: Should use global elapsed in case there was a stall since the last time this samp was accessed
            horizvol=q3.value(0)+estvol
            self.sampInfo[sampid]=(estvol,horizvol,finalvol,lastop)
        print("->",self.sampInfo[sampid])
        return self.sampInfo[sampid]

    def getTotalNeeded(self):
        """Calculate amount of sampid needed through end of run"""

    def refreshRunsTable(self):
        # q=QtSql.QSqlQueryModel()
        # q.setQuery("SELECT r.run, right(r.run,4) runid, program, logfile, starttime, endtime from runs r order by starttime desc")
        # self.sqlErrorCheck(q.lastError())
        q=RunsModel()
        q.update()
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
        q=self.dbget("SELECT p.name, date_format(gentime,'%%m/%%d/%%y %%H:%%i'), date_format(starttime,'%%m/%%d/%%y %%H:%%i'), date_format(endtime,'%%m/%%d/%%y %%H:%%i'),r.logfile, r.lineno, r.status from runs r, programs p where r.program=p.program and r.run='%s' group by r.run order by starttime desc"%self.currentRun)
        if not q:
            self.currentRun=None
            return
        self.programName.setText(q.value(0)+" "+q.value(4))
        print("q.value(1)=",q.value(1))
        self.generated.setText("Gen: "+q.value(1))
        self.starttime.setText("Start: "+q.value(2))
        self.status.setText(q.value(6))
        print("q.value(3)=",q.value(3))
        q2=self.dbget("SELECT measured,elapsed FROM v_vols WHERE run=%d ORDER BY measured DESC LIMIT 1"%self.currentRun)
        if q2 is None:
            print("No vol data")
            return
        self.lastMeasured=q2.value(0)
        self.lastElapsed=q2.value(1)
        q3=self.dbget("SELECT max(elapsed) FROM ops WHERE program=%d"%self.currentProgram)
        self.endElapsed=q3.value(0)
        self.endTime=self.lastMeasured.addSecs(self.endElapsed-self.lastElapsed)
        if q.value(3) is not None and q.value(3)!="":
            self.endtime.setText("End: "+q.value(3))
            self.lineno.setText("Done")
        else:
            self.endtime.setText("Last: %s, End: %s"%(self.lastMeasured.toString('MM/dd/yy HH:mm'),self.endTime.toString('MM/dd/yy HH:mm')))
            self.lineno.setText("Elapsed: %.0f, Line: %s"%(self.lastElapsed/60.0,str(q.value(5))))

    def refreshPlatesTable(self):
        q=QtSql.QSqlQueryModel()
        query="SELECT plate,count(*) numsamps from samples s where s.program=(select program from runs where run='%s') group by plate order by plate"%self.currentRun
        print(query)
        q.setQuery(query)
        if q.lastError().isValid():
            self.dbreopen()
            q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.plateTable.setModel(q)
        self.plateTable.resizeColumnsToContents()

    def refreshSamplesTable(self):
        query="""
            select sample,well,name,min(elapsed),max(elapsed)
            from v_ops
            where plate='%s' and program=%d
            and cmd!='Detect_Liquid'
            and cmd!='Initial'
            group by sample,well,name
            order by right(well,length(well)-1)+0,well
            """%(self.currentPlate, self.currentProgram)
        print(query)
        q=QtSql.QSqlQuery(query)
        if q.lastError().isValid():
            self.dbreopen()
            q = QtSql.QSqlQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.sampleTable.setColumnCount(7)
        data=[]
        while q.next():
            sampInfo = self.getSampData(q.value(0),self.horizonHours.value())
            data.append([q.value(0),q.value(1),q.value(2),"%.0f-%.0f"%(q.value(3)/60,q.value(4)/60) if q.value(4)>self.lastElapsed else "Done",sampInfo[0],sampInfo[1],sampInfo[2]])
        self.sampleTable.setRowCount(len(data))
        for r in range(len(data)):
            for c in range(len(data[r])):
                if c==0:
                    item = QTableWidgetItem("%d"%data[r][c])
                elif c>=4:
                    item = QTableWidgetItem("%.1f"%data[r][c])
                    if data[r][c]<15:
                        item.setBackground(QColor("red"))
                    elif data[r][c] < 30:
                        item.setBackground(QColor("yellow"))
                else:
                    item = QTableWidgetItem(data[r][c])
                self.sampleTable.setItem(r,c,item)

        #query = "select s.sample,s.well,s.name  from samples s where s.plate='%s' and s.program=%d order by right(s.well,length(s.well)-1),s.well;" % (self.currentPlate, self.currentProgram)
        self.sampleTable.setColumnHidden(0,True)
        self.sampleTable.setHorizontalHeaderItem(1,QTableWidgetItem("Well"))
        self.sampleTable.setHorizontalHeaderItem(2,QTableWidgetItem("Name"))
        self.sampleTable.setHorizontalHeaderItem(3,QTableWidgetItem("Elapsed"))
        self.sampleTable.setHorizontalHeaderItem(4,QTableWidgetItem("Cur Vol"))
        self.sampleTable.setHorizontalHeaderItem(5,QTableWidgetItem("Vol in %.0f hrs"%self.horizonHours.value()))
        self.sampleTable.setHorizontalHeaderItem(6,QTableWidgetItem("End Vol"))
        self.sampleTable.resizeColumnsToContents()

    def refreshSampleDetail(self):
        print("currentSample=",self.currentSample)
        query = "SELECT name,plate,well FROM samples WHERE sample=%d" % self.currentSample
        print(query)
        q=QtSql.QSqlQuery(query)
        if q.lastError().isValid():
            self.dbreopen()
            q = QtSql.QSqlQuery(query)
        self.sqlErrorCheck(q.lastError())
        q.next()
        self.sampleName.setText(q.value(0))
        self.wellName.setText(q.value(1)+"."+q.value(2))
        vquery="""
            SELECT estvol+volchange
            FROM v_vols
            WHERE plate='%s' AND run=%d AND sample=%d
            ORDER BY lineno DESC
            LIMIT 1
            """%(self.currentPlate,self.currentRun,self.currentSample)
        print(vquery)
        q = QtSql.QSqlQuery(vquery)
        if q.lastError().isValid():
            self.dbreopen()
            q = QtSql.QSqlQuery(vquery)
        self.sqlErrorCheck(q.lastError())
        q.next()
        if q.value(0) is None:
            self.volume.setText("?")
        else:
            self.volume.setText("%.1f"%q.value(0))

    def refreshVolsTable(self):
        q=QtSql.QSqlQueryModel()
        query="""
            select lineno,measured, round(elapsed/60.0,1) elapsed,cmd,tip,round(estvol,1) estvol, ifnull(round(obsvol,1),if(zmax,'FAIL','NM'))  observed,round(obsvol-estvol,1) diff,round(volchange,1) volchange 
            from v_vols 
            where run='%s' and sample=%d 
            order by lineno
            """%(self.currentRun, self.currentSample)
        print(query)
        q.setQuery(query)
        if q.lastError().isValid():
            self.dbreopen()
            q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.volsTable.setModel(q)
        # ind=self.volsTable.model().createIndex(2,2)
        # self.volsTable.model().setData(ind,"Hello")
        self.volsTable.resizeColumnsToContents()

    def refreshOpsTable(self):
        sdata=self.getSampData(self.currentSample,self.horizonHours.value())
        print("sdata=",sdata)
        q=QtSql.QSqlQueryModel()
        query="""
            select lineno,timestampadd(second,elapsed-%f,str_to_date('%s','%%m/%%d/%%y %%H:%%i')) projected,round(elapsed/60.0,1) elapsed,cmd,tip,round(volchange,1) volchange 
            from v_ops o
            where program=%d and sample=%d and op>%d
            and volchange!=0
            order by lineno
            """%(self.lastElapsed,self.lastMeasured.toString('MM/dd/yy HH:mm'),self.currentProgram, self.currentSample, sdata[3])
        print(query)
        q.setQuery(query)
        if q.lastError().isValid():
            self.dbreopen()
            q.setQuery(query)
        self.sqlErrorCheck(q.lastError())
        self.opsTable.setModel(q)
        self.opsTable.resizeColumnsToContents()

    def refreshPlateGroup(self):
        print("refreshPlateGroup: plate=",self.currentPlate)
        if self.currentPlate is None:
            self.sampleTable.hide()
            self.currentWell=None
            return
        self.sampleTable.show()
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
        self.refreshOpsTable()
        self.sampleGroup.layout()

    def refreshAll(self):
        self.dbcheck()
        self.sampInfo={}
        self.refreshRunsTable()
        self.refreshRunGroup()
        self.refreshPlateGroup()
        self.refreshSampleGroup()
        self.central.layout()

    def runs(self,arg):
        print("runs",arg)

    def selectRun(self,index: QModelIndex):
        print("select row",index.row(),"column",index.column(),"id",index.internalId())
        pkIndex=index.sibling(index.row(),0)

        self.currentRun=self.runsTable.model().data(pkIndex).value()
        pgmIndex=index.sibling(index.row(),3)
        self.currentProgram=self.runsTable.model().data(pgmIndex).value()
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
        self.currentWell=self.sampleTable.item(index.row(),1).text()
        print("sample item=",self.sampleTable.item(index.row(),0).text())
        self.currentSample=int(self.sampleTable.item(index.row(),0).text())
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
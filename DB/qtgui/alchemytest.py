# Quick test of using SQL Alchemy to access database (11/14/2019)
# Not integrated with any other parts

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date, Float, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import sessionmaker, relationship, selectinload

Base = declarative_base()

class Programs(Base):
    __tablename__ = 'programs'
    program = Column(Integer, primary_key=True)
    name = Column(String)
    gentime = Column(Date)
    checksum = Column(String)
    gitlabel = Column(String)
    totaltime = Column(Float)
    complete = Column(Boolean)
    runs = relationship("Runs", back_populates="program")
    ops = relationship("Ops", back_populates="program")
    samples = relationship("Samples", back_populates="program")

    def __repr__(self):
        return "<Program(program=%d, name='%s')>" % (self.program, self.name)

class Runs(Base):
    __tablename__ = 'runs'
    run = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program'), name="program")
    program = relationship("Programs",back_populates='runs', uselist=False, lazy="selectin")
    logfile = Column(String)
    starttime = Column(Date)
    endtime = Column(Date)
    lineno = Column(Integer)
    firstline = Column(Integer)
    expt = Column(Integer)
    logheader = Column(String)
    status = Column(String)
    vols = relationship("Vols", back_populates="run")

    def __repr__(self):
        return "<Run(run='%s', program='%s', logfile='%s', start='%s')>" % \
               (self.run, self.program, self.logfile, self.starttime)

class Samples(Base):
    __tablename__="samples"
    sample = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program'), name="program")
    program = relationship("Programs",back_populates='samples', uselist=False)
    plate = Column(String)
    well = Column(String)
    name = Column(String)
    def __repr__(self):
        return "<Sample(%s@%s.%s)>" % (self.name, self.plate, self.well)

class LiquidClasses(Base):
    __tablename__='liquidclasses'
    lc = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return "<LC(%s)>"%(self.name)

class Ops(Base):
    __tablename__='ops'
    op=Column(Integer,primary_key=True)
    program_id=Column(Integer, ForeignKey('programs.program'), name="program")
    program=relationship("Programs",back_populates='ops')
    sample_id=Column(Integer, ForeignKey('samples.sample'), name="sample")
    cmd=Column(String)
    lineno=Column(Integer)
    elapsed=Column(Float)
    tip=Column(Integer)
    lc_id=Column(Integer, ForeignKey('liquidclasses.lc'), name='lc')
    lc=relationship("LiquidClasses", uselist=False, lazy="joined")
    volchange=Column(Float)
    clean=Column(Boolean)
    def __repr__(self):
        return "<Op(%s@%d)>"%(self.cmd,self.lineno)

class Vols(Base):
    __tablename__='vols'

    vol=Column(Integer, primary_key=True)
    run_id=Column(Integer, ForeignKey('runs.run'), name="run")
    run=relationship("Runs",back_populates='vols', uselist=False)
    op_id=Column(Integer, ForeignKey('ops.op'), name="op")
    op=relationship("Ops",uselist=False,lazy="joined")
    estvol=Column(Float)
    gemvolume=Column(Float)
    volume=Column(Float)
    height=Column(Integer)
    submerge=Column(Integer)
    zmax=Column(Integer)
    zadd=Column(Integer)
    measured=Column(Date)
    def __repr__(self):
        return "<Vol(%d,%d,%s)>"%(self.run_id,self.op_id, self.volume)

engine = create_engine("mysql+pymysql://ngsreadonly:@35.203.151.202/robot", echo=True)
Session = sessionmaker(bind=engine)
session = Session()

runs=session.query(Runs)
for run in runs[0:10]:
    print(run, run.program)
    if run.program is not None:
        for op in run.program.ops[0:3]:
            print(" ",op,op.lc)
    for vol in run.vols[10:13]:
        print(" ",vol.op,vol.op.lc,vol)


for program  in session.query(Programs):
     print(program)

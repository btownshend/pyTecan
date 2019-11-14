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
    def __repr__(self):
        return "<Program(program=%d, name='%s')>" % (self.program, self.name)

class Runs(Base):
    __tablename__ = 'runs'
    run = Column(Integer, primary_key=True)
    program_id = Column(Integer, ForeignKey('programs.program'), name="program")
    program = relationship("Programs",back_populates='runs')
    logfile = Column(String)
    starttime = Column(Date)
    endtime = Column(Date)
    lineno = Column(Integer)
    firstline = Column(Integer)
    expt = Column(Integer)
    logheader = Column(String)
    status = Column(String)

    def __repr__(self):
        return "<Run(run='%s', program='%s', logfile='%s', start='%s')>" % \
               (self.run, self.program, self.logfile, self.starttime)


Programs.runs = relationship("Runs", order_by=Runs.run, back_populates="program")

engine = create_engine("mysql+pymysql://ngsreadonly:@35.203.151.202/robot", echo=True)
Session = sessionmaker(bind=engine)
session = Session()

for run  in session.query(Runs).options(selectinload(Runs.program)):
    print(run, run.program)


# for program  in session.query(Programs):
#     print(program)

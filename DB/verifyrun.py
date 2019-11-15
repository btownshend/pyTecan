import argparse
import logging
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from robotorm import Runs


class VerifyRun(object):
    def __init__(self):
        # Setup logging
        fname = time.strftime("verifyrun-%Y%m%d.log")
        logging.basicConfig(filename=fname, level=logging.DEBUG, format='%(asctime)s %(levelname)s:\t %(message)s')
        logging.captureWarnings(True)
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        self.console.setFormatter(formatter)
        logging.getLogger('').addHandler(self.console)
        engine = create_engine("mysql+pymysql://ngsreadonly:@35.203.151.202/robot", echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def execute(self, argv):
        logging.info("Running: %s", " ".join(argv))

        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
        parser.add_argument("-r", "--run", help="run ID")
        args = parser.parse_args()

        if args.verbose:
            print("verbosity turned on")
            self.console.setLevel(logging.DEBUG)
        run=self.getrun(args.run)
        print("Got run: ",run)
        if run is not None:
            return self.verifyrun(run)
        return 0

    def getrun(self,runid):
        print("runid=",runid)
        if runid is None:
            currentrun = self.session.query(Runs).filter(Runs.endtime is None).first()
            if currentrun is not None:
                print("Current run: ",currentrun)
                return currentrun
        else:
            run = self.session.query(Runs).filter(Runs.run == runid).one()
            return run
        return None

    def volerror(self, msg, vol):
        print("Volume error: %s"%msg)
        print(" ",vol.op.sample)
        print(" ",vol.op)
        print(" ",vol)
        print("")

    def verifyrun(self, run):
        """Run a verification of run and return 0 if ok"""
        for vol in run.vols:
            if vol.volume is None:
                if vol.op.cmd!="Detect_Liquid" and vol.estvol>30 and vol.zmax is not None:
                    # Undetected,but should have
                    self.volerror("LD failure (ZMax=%s)"%(vol.zmax),vol)
            elif vol.estvol is not None and vol.estvol>=20:
                if vol.op.sample.plate!="Water" and vol.op.sample.plate!="Bleach":  # Skip troughs
                    # Check if this was the first access
                    nprior=len([ v for v in run.vols if v.op.sample_id==vol.op.sample_id and v.vol<vol.vol])

                    diff=vol.volume-vol.estvol
                    if abs(diff)>10 and nprior>1:  # Ignore first measurement since initial estimate may have been off
                        self.volerror("Volume diff of %.0f"%(diff),vol)
        return 0

# Execute the application
if __name__ == "__main__":
    exitCode = -1
    # noinspection PyBroadException,PyPep8
    try:
        db = VerifyRun()
        exitCode = db.execute(sys.argv)
        logging.info('Exit code %d', exitCode)
    except:
        (typ, val, tb) = sys.exc_info()
        logging.error("Exception: %s", str(typ))
        import traceback

        logging.error(traceback.format_exc(tb))
    sys.exit(int(exitCode))

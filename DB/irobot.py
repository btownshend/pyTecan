import argparse
import logging
import sys
import time

import pandas
import pymysql.cursors


class IRobot(object):
    def __init__(self):
        # Setup logging
        fname = time.strftime("irobot-%Y%m%d.log")
        logging.basicConfig(filename=fname, level=logging.DEBUG, format='%(asctime)s %(levelname)s:\t %(message)s')
        logging.captureWarnings(True)
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        self.console.setFormatter(formatter)
        logging.getLogger('').addHandler(self.console)
        self.con = None
        pandas.set_option('display.width', 200)

    def execute(self, argv):
        logging.info("Running: %s", " ".join(argv))

        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
        parser.add_argument("-r", "--run", help="run ID")
        args = parser.parse_args()
        retval = -1
        if args.verbose:
            print("verbosity turned on")
            self.console.setLevel(logging.DEBUG)
        try:
            # Open database connection
            self.con = pymysql.connect(host='35.203.151.202', user='robot', password='cdsrobot', db='robot',
                                       cursorclass=pymysql.cursors.DictCursor)
            with self.con.cursor() as cursor:
                cursor.execute("set time_zone='US/Pacific'")
            if args.run is None:
                args.run = self.getrun()
                if args.run is None:
                    args.run = '%'  # Show all runs
            retval = self.showrun(args.run)
        finally:
            self.con.close()

        return retval

    def getrun(self):
        """Get Current run"""
        with self.con.cursor() as cursor:
            cursor.execute("select run from runs where endtime is null")
            res = cursor.fetchall()
            if len(res) != 1:
                logging.error('getrun: Unable to retrieve current run, have %d entries with null endtime', len(res))
                return None
            print("res=", res)
            run = res[0]['run']
            logging.info('run=%s', run)
        return run

    def showrun(self, run):
        df = pandas.read_sql_query("select * from runs where run like '%%%s%%' order by starttime" % (run,),
                                   self.con)
        print(df)
        return 0


# Execute the application
if __name__ == "__main__":
    exitCode = -1
    # noinspection PyBroadException,PyPep8
    try:
        db = IRobot()
        exitCode = db.execute(sys.argv)
        logging.info('Exit code %d', exitCode)
    except:
        (typ, val, tb) = sys.exc_info()
        logging.error("Exception: %s", str(typ))
        import traceback

        logging.error(traceback.format_exc(tb))
    sys.exit(int(exitCode))

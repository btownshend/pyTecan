import os

from Experiment.experiment import Experiment
from Experiment import worklist

e=Experiment()

worklist.pyrun('PTC\\ptcsetpgm.py TEST TEMP@95,1  TEMP@25,1')
e.runpgm("TEST",0,waitForCompletion=False)
e.waitpgm(sanitize=False)

e.savegem("platemovetest_orig.gem")

os.system("grep -v 'Wash\|reagent tubes' platemovetest_orig.gem  > platemovetest.gem")

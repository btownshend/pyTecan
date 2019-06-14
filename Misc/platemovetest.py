import os

from Experiment.experiment import Experiment
from Experiment import worklist, decklayout

e=Experiment()

worklist.pyrun('PTC\\ptcsetpgm.py TEST TEMP@95,1  TEMP@25,1',version=2)
e.runpgm(decklayout.SAMPLEPLATE, "TEST",0,waitForCompletion=False)
e.waitpgm(sanitize=False)

e.savegem("platemovetest_orig.gem")

os.system("grep -v 'Wash\|reagent tubes' platemovetest_orig.gem  > platemovetest.gem")

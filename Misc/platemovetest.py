import os

from Experiment.sample import Sample
from Experiment.experiment import Experiment
from Experiment.experiment import Concentration

e=Experiment()

e.w.pyrun('PTC\\ptcsetpgm.py TEST TEMP@95,1  TEMP@25,1')
e.runpgm("TEST",0,waitForCompletion=False)
e.waitpgm(sanitize=False)

e.savegem("platemovetest_orig.gem")

os.system("grep -v 'Wash\|reagent tubes' platemovetest_orig.gem  > platemovetest.gem")

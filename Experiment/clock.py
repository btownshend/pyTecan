"""Keep track of elapsed time of run"""

pipetting=0
pipandthermotime=0
thermotime=0		# Time waiting for thermocycler without pipetting
totalTime=None

def reset(total: float = None):
    global pipetting, pipandthermotime,thermotime,totalTime
    pipetting=0
    pipandthermotime=0
    thermotime=0		# Time waiting for thermocycler without pipetting
    totalTime=total

def elapsed() -> float:
    return pipetting+pipandthermotime+thermotime

def statusString() -> str:
    if totalTime is not None:
        # noinspection PyTypeChecker
        return "Estimated elapsed: %d minutes, remaining run time: %d minutes"%(elapsed()/60,(totalTime-elapsed())/60)
    else:
        return "Estimated elapsed: %d minutes"%(elapsed()/60)

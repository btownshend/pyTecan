python bioexec.py setElmLockPos
sleep 2
python bioexec.py setShakeTargetSpeed1200
python bioexec.py setShakeAcceleration5
python bioexec.py shakeOn
sleep $1
python bioexec.py shakeOff
sleep 6
python bioexec.py setElmUnlockPos

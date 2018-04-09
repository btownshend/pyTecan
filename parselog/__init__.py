__all__=["datalog","parselog","embedded"]

from sys import version_info, exit
if version_info < (3,5):
    print("pyTecan now requires python 3.5 or later (called with %d.%d)"%(version_info[0],version_info[1]))
    exit(1)
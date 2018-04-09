class Embedded:
    """Support for python calls embedded into a log file"""
    def startrun(self,id,lineno,elapsed,name,gentime,checksum,gitlabel,totalTime):
        print("startrun: id=%d,lineno=%d,elapsed=%f,name=%s,gentime=%s,checksum=%s,gitlabel=%s,totalTime=%f"%(id,lineno,elapsed,name,gentime,checksum,gitlabel,totalTime))

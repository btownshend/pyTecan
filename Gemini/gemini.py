# Gemini interface module

from win32file import *
from win32pipe import *
from win32api import *
import string

class Gemini(object):
	debug=False
	hPipe=None

	# An exception in the communications with Gemini
	class IOException(BaseException):
		pass
	# A command error
	class CmdError(BaseException):
		pass

	errorDescs = [ 'No Error', 'Invalid command','Unexpected error','Invalid number of operands','Invalid operand','RSP error reported in answer string','RSP not initialized','ROMA-vector not defined','ROMA-vector for this site is not defined','RSP still active','RSP not active','RSP not active(11)','Cancel was pressed','Script could not be loaded/saved','Variable not defined','Advanced version of Gemini required','No rack gripped by ROMA','Device not found','Timeout','Worklist already loaded']

	def execute(self,cmd):
		try:
			WriteFile(self.hPipe,cmd)
		except:
			err=GetLastError()
			print "I/O Error during WriteFile:",FormatMessage(err)
			raise self.IOException()
		try:
			(hr,str)=ReadFile(self.hPipe,1024)
		except:
			err=GetLastError()
			print "I/O Error during ReadFile:",FormatMessage(err)
			raise self.IOException()
		if self.debug:
			print "cmd=%s, hr=%d, str=%s"%(cmd,hr,str)
		if str[len(str)-1]=='\0':
			str=str[0:len(str)-1]
		res=string.splitfields(string.strip(str),';')
		ecode=int(res[0])
		if ecode!=0:
			print "Error executing command <%s>: %s (%d)"%(cmd,self.errorDescs[ecode],ecode)
			raise self.CmdError(ecode)
		return res[1:]

	def setdebug(self):
		self.debug=True

	def flush(self):
		while True:
			(hr,str)=ReadFile(self.hPipe,1024)
			if hr!=0:
				break
			print "Flush: hr=",hr,", str=<",str,">"

	def getvar(self,name):
		try:
			resp=self.execute('GET_VARIABLE;%s'%name)
		except self.CmdError, ecode:
			print "caught, ecode=",ecode
			if ecode==14:
				print "Variable not found: ",name
				return None
			else:
				print "unexpected error: %d"%ecode
				raise self.CmdError(ecode)
		return float(resp[0])

	def getstatus(self):
		status=self.execute("GET_STATUS")
		return status[0]

	def getversion(self):
		result=self.execute("GET_VERSION")
		return result[0]

	def setvar(self,name,value):
		try:
			resp=self.execute('SET_VARIABLE;%s;%.2f'%(name,value))
		except self.CmdError,ecode:
			print "Error setting %s to %f: %s"%(name,value,str(ecode))
			raise
		return resp

	def start_pipetting(self):
		resp=self.execute("START_PIPETTING")
		return resp

	def close(self):
		pass

	def open(self):
		pipeName= "\\\\.\\pipe\\gemini"
		while True:
			if self.debug:
				print "Attempting to open %s"%pipeName
			try:
				self.hPipe = CreateFile(pipeName, GENERIC_READ | GENERIC_WRITE,0, None,OPEN_EXISTING,0,None)
			except:
				err=GetLastError()
				print "Error while opening pipe to Gemini at ",pipeName,":",FormatMessage(err)
				raise self.IOException()

			# Break if the pipe handle is valid.
			if self.hPipe != INVALID_HANDLE_VALUE:
				if self.debug:
					print "CreateFile succeeded"
				break
			# Exit if an error other than ERROR_PIPE_BUSY occurs.
			if GetLastError() != ERROR_PIPE_BUSY:
				print "Could not open pipe"
				exit(-1)
			# All pipe instances are busy, so wait for 2 seconds.
			print "Waiting for pipe...",
			if  not WaitNamedPipe(pipeName, 2000):
				print "WaitNamedPipe failed"
				exit(-1)
			print "done"

		# The pipe connected; change to message-read mode.
		try:
			SetNamedPipeHandleState(self.hPipe,PIPE_READMODE_MESSAGE,None,None)
		except:
			print "Error in SetNamedPipeHandleState"
			exit(-1)
		if self.debug:
			print "Pipe ready"

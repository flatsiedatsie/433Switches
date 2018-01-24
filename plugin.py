"""
<plugin key="RFSwitches" name="RFSwitches" author="blauwebuis" version="1.0.0" wikilink="https://www.domoticz.com/wiki/Plugins/RFSwitches" externallink="https://www.domoticz.com/forum/viewtopic.php?f=65&t=21567">
	<description>
		This plugin creates a new "learning" switch. Everytime you turn it on and off, you create a new RF switch. 
		When you set this switch to "on", the plugin starts listening for your remote control's commands for 10 seconds. Hold your remote close the the receiver, and press your remote's on button a few times during that period. 
		Next, turn the learning switch back to off. Now you again have 10 seconds to press the off buton on your RF remote control a few times. 
		If you refresh the switches page, you will find a new RF switch that has just been created, and that is connected to the two recordings you just made.
	</description>
	<params>
		<param field="Mode1" label="Transmitter data GPIO pin" width="30px" required="true" default="17"/>
		<param field="Mode2" label="Receiver data GPIO pin"	width="30px" required="true" default="27"/>
		<button>test</button>
	</params>
</plugin>
"""
try:
	import Domoticz
except ImportError:
	import fakeDomoticz as Domoticz
from subprocess import call
import platform
import os
import subprocess
import time
import sys



class BasePlugin:

	def __init__(self):
		self.platform = platform.system()	
		self.txpin = 17
		self.rxpin = 27
		self.command = ""
		self.dirName = os.path.dirname(__file__)
		return 

	def onStart(self):
		Domoticz.Debugging(1)
		
		# start the PiGPIO deamon, just is case it hasn't been started yet.
		command = str("/home/dietpi/domoticz/plugins/RFSwitches/startd.sh")
		dstarter = os.popen(command).read()
		
		# create the listen-toggle-switch. This controls the making of new RF switches.
		if 1 not in Devices:
			Domoticz.Log("Creating the master 433 learn switch. Use if to add new switches.")
			Domoticz.Device(Name="Learn 433 switch", Unit=1, TypeName="Switch", Image=9, Used=1).Create()
		
		self.txpin=Parameters["Mode1"]
		self.rxpin=Parameters["Mode2"]

		Domoticz.Log("RFSwitches TX pin = " + str(Parameters["Mode1"]))
		Domoticz.Log("RFSwitches RX pin = " + str(Parameters["Mode2"]))
		Domoticz.Log("Python location = " + str(Parameters["Address"]))
		Domoticz.Log("RF Switches made so far (max 255): " + str(len(Devices)))
		
		return
		
	def onStop(self):
		Domoticz.Log("onStop called")

	def onConnect(self, Connection, Status, Description):
		Domoticz.Log("onConnect called")

	def onMessage(self, Connection, Data, Status, Extra):
		Domoticz.Log("onMessage called")

	def onCommand(self, Unit, Command, Level, Hue):
		Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))		
		
		#first, let's flip the switch.
		if str(Command) == "On":
			Devices[Unit].Update(nValue=1,sValue="On")
		if str(Command) == "Off":
			Devices[Unit].Update(nValue=0,sValue="Off")
		
		action = "play"
		recordingName = str(Unit) + str(Command)
		
		#If the learner switch was flipped, let's record new codes and create a new switch.
		if Unit == 1:
			action = "record"
			nextDevice = len(Devices) + 1
			recordingName = str(nextDevice) + str(Command)
			
			#When the off button is clicked, we create the new switch.
			if str(Command) == "Off": 
				nextName = "New RF switch #" + str(nextDevice)
				Domoticz.Device(Name=nextName, Unit=nextDevice, TypeName="Switch", Image=9, Used=1).Create()
				Domoticz.Log("New RF Switch created, #" + str(nextDevice))
			
		#command = str(self.dirName) + "/RFSwitches.sh " + str(sys.executable) + " " + str(self.dirName) + "/433cloner.py " + str(self.txpin) + " " + str(self.rxpin) + " " + action + " " + recordingName
		#Domoticz.Log(str(command))
		#cloner = os.popen(command).read()
		
		callCommand = "sudo " + str(sys.executable) + " " + str(self.dirName) + "/433cloner.py --txpin " + str(self.txpin) + " --rxpin " + str(self.rxpin) + " " + action + " " + recordingName
		Domoticz.Log(str(callCommand))
		try:
			call (callCommand, shell=True)
		Except:
			cloner = os.popen(command).read()

	def onHeartbeat(self):
		pass


global _plugin
_plugin = BasePlugin()

def onStart():
	global _plugin
	_plugin.onStart()

def onStop():
	global _plugin
	_plugin.onStop()

def onCommand(Unit, Command, Level, Hue):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Hue)

def onHeartbeat():
	#pass
	global _plugin 
	_plugin.onHeartbeat()
	

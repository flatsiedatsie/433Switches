#!/usr/bin/env python
"""
<plugin key="RFSwitches" name="RFSwitches" author="blauwebuis" version="1.0.0" wikilink="http://www.domoticz.com/wiki/plugins/433switches.html" externallink="https://www.slashdot.org/">
    <params>
        <param field="Mode1" label="Transmitter data GPIO pin" width="30px" required="true" default="17"/>
        <param field="Mode2" label="Receiver data GPIO pin"    width="30px" required="true" default="27"/>
    </params>
</plugin>
"""
import Domoticz
from subprocess import call

class BasePlugin:

    def __init__(self):
        self.txpin = 17
        self.rxpin = 27
        return 

    def onStart(self):
        Domoticz.Log("onStart called")
        Domoticz.Debugging(1)
        # create the listen-toggle-switch. This controls the making of new RF switches.
        if 1 not in Devices:
            Domoticz.Log("Creating the master 433 learn switch. Use if to add new switches.")
            Domoticz.Device(Name="Learn 433 switch", Unit=1, TypeName="Switch", Image=9, Used=1).Create()
            #devicecreated.append(deviceparam(3, 0, ""))  # default is Off

        #if Devices[1].sValue == "0":
        #    Domoticz.Log("433 learning switch was OFF at start")
             
        #if Devices[1].sValue == "1":    
        #    Domoticz.Log("433 learning switch was ON at start")
        
        self.txpin=Parameters["Mode1"]
        self.rxpin=Parameters["Mode2"]

        Domoticz.Log("RFSwitches TX pin = " + str(Parameters["Mode1"]))
        Domoticz.Log("RFSwitches RX pin = " + str(Parameters["Mode2"]))
        #Domoticz.Log("Device count: " + str(len(Devices)))
        return
        
    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data, Status, Extra):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))
        if Unit == 1:
            # The user is creating a new RF switch
            nextDevice = len(Devices) + 1
            name_on  = str(nextDevice) + "On"
            name_off = str(nextDevice) + "Off"
            
            if str(Command) == "On": 
                Domoticz.Device(Name="I am a new 433 switch", Unit=nextDevice, TypeName="Switch", Image=9, Used=1).Create()
                Domoticz.Log("Switch created, now recording ON command")
                name_on = str(nextDevice) + "On"
                svalue = 'press on'
                Devices[Unit].Update(nValue=1,sValue=svalue)
                call(["python3", "433cloner.py", "--rxpin", str(self.rxpin), "record", name_on])
                
                
            if str(Command) == "Off":
                Domoticz.Log("Now recording OFF command") 
                svalue = "press off"
                Devices[Unit].Update(nValue=0,sValue=svalue)
                call(["python3", "433cloner.py", "--rxpin", str(self.rxpin), "record", name_off])
                
        else:
            # The user is using an existing RF switch
            if str(Command) == "On":
                svalue = 'on'
                Devices[Unit].Update(nValue=1,sValue=svalue)
            
            if str(Command) == "Off":
                svalue = "off" 
                Devices[Unit].Update(nValue=0,sValue=svalue)          
            
            recordingName = str(Unit) + str(Command)
            Domoticz.Log("playing back RF recording: " + recordingName)
            call(["python3", "433cloner.py", "--txpin", str(self.txpin), "play", recordingName])
                
    def onHeartbeat(self):
        x = 1
        
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

#def onHeartbeat():
#    global _plugin 
#    _plugin.onHeartbeat()



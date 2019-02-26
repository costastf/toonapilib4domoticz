# ToonApiLib for Domoticz
# by John van de Vrugt
#
"""
<plugin key="ToonApiLib" name="ToonApiLib" author="John van de Vrugt" version="1.0.8" wikilink="https://github.com/JohnvandeVrugt/toonapilib4domoticz">
    <description>
    </description>
    <params>
        <param field="Username" label="Eneco user" required="true"/>
        <param field="Password" label="Eneco pass" required="true" password="true"/>
        <param field="Mode1" label="Consumer key" required="true"/>
        <param field="Mode2" label="Consumer secret" required="true" password="true"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal" default="true" />
            </options>
        </param>
    </params>
</plugin>
"""
import Domoticz
from toonapilib import Toon


DEBUG_PRINT = Parameters["Mode6"] == "Debug"

class BasePlugin:

    enabled = False

    def __init__(self, heartbeat=0):
        self.toon = None
        self.heartbeat = heartbeat

    def _get_toon(self):
        try:
            myname = Parameters["Username"]
            mypass = Parameters["Password"]
            mykey = Parameters["Mode1"]
            mysecret = Parameters["Mode2"]
            if DEBUG_PRINT:
                Domoticz.Log("Creating Toon object")
            MyToon = Toon(myname, mypass, mykey, mysecret)
        except Exception:
            MyToon = None
            Domoticz.Log("Could not create a toon object")
            Domoticz.Log("Possible solution:")
            Domoticz.Log("* Check your credentials")
            Domoticz.Log("* Restart domoticz")
        return MyToon

    def onStart(self):
        if DEBUG_PRINT:
            Domoticz.Log("Starting toonapilib4domoticz with debug logging")
        self.toon = self._get_toon()
        if self.toon:
            #check for devices
            if not len(Devices):
                Domoticz.Log("Creating Toon devices")
                try:
                    Domoticz.Device(Name="Power usage", Unit=1, Type=250, Subtype=1).Create()
                    Domoticz.Device(Name="Gas usage", Unit=2, Type=251, Subtype=2).Create()
                    Domoticz.Device(Name="Room temperature", Unit=3, Type=80, Subtype=5).Create()
                    Domoticz.Device(Name="Setpoint", Unit=4, Type=242, Subtype=1).Create()
                    Domoticz.Device(Name="Heating active", Unit=5, Type=244, Subtype=62, Switchtype=0).Create()
                    Domoticz.Device(Name="Hot water active", Unit=6, Type=244, Subtype=62, Switchtype=0).Create()
                    Domoticz.Device(Name="Preheat active", Unit=7, Type=244, Subtype=62, Switchtype=0).Create()
                except Exception:
                    Domoticz.Log("An error occured while creating Toon devices")
                #add scenes
                Options = {"LevelNames": "Unknown|Away|Sleep|Home|Comfort",
                           "LevelOffHidden": "true",
                           "SelectorStyle": "0"}
                Domoticz.Device(Name="Scene", Unit=8, TypeName="Selector Switch", Options=Options).Create()
            else:
                self.update_devices()

    def onStop(self):
        Domoticz.Log("onStop called")

    def onConnect(self, Connection, Status, Description):
        Domoticz.Log("onConnect called")

    def onMessage(self, Connection, Data):
        Domoticz.Log("onMessage called")

    def onCommand(self, Unit, Command, Level, Hue):
        if DEBUG_PRINT:
            Domoticz.Log(("onCommand called for Unit {unit}: "
                          "Parameter '{command}', Level: {level}").format(unit=Unit,
                                                                          command=Command,
                                                                          level=Level))
        try:
            if Unit == 4:
                self.toon.thermostat = Level
                Domoticz.Log("set level {level}".format(level=Level))
                szSetpoint = str(self.toon.thermostat)
                Devices[4].Update(0, szSetpoint)
        except Exception:
            Domoticz.Log("An error occurred setting the thermostat")

    def onNotification(self, Name, Subject, Text, Status, Priority, Sound, ImageFile):
        Domoticz.Log("Notification: {text}".format(text=','.join([Name,
                                                                  Subject,
                                                                  Text,
                                                                  Status,
                                                                  Priority,
                                                                  Sound,
                                                                  ImageFile])))

    def onDisconnect(self, Connection):
        Domoticz.Log("onDisconnect called")

    def onHeartbeat(self):
        self.heartbeat += 1
        if self.heartbeat == 12:
            self.heartbeat = 0
            self.update_devices()

    def update_devices(self):
        if self.toon:
            try:
                values = [self.toon.power.meter_reading_low,
                          self.toon.power.meter_reading,
                          self.toon.solar.meter_reading_low_produced,
                          self.toon.solar.meter_reading_produced,
                          self.toon.power.value,
                          self.toon.solar.value]
                szPower = ';'.join([str(value) for value in values])
                if DEBUG_PRINT:
                    Domoticz.Log("Update power/solar usage: {power}".format(power=szPower))
                Devices[1].Update(0, szPower)
            except Exception:
                Domoticz.Log("An error occured updating power usage")
            try:
                szGas = str(self.toon.gas.daily_usage)
                if DEBUG_PRINT:
                    Domoticz.Log("Update gas usage: " + szGas)
                Devices[2].Update(0, szGas)
            except Exception:
                Domoticz.Log("An error occured updating gas usage")
            try:
                szTemp = str(self.toon.temperature)
                if DEBUG_PRINT:
                    Domoticz.Log("Update temperature: " + szTemp)
                Devices[3].Update(0, szTemp)
            except Exception:
                Domoticz.Log("An error occured updating temperature")
            try:
                szSetpoint = str(self.toon.thermostat)
                if DEBUG_PRINT:
                    Domoticz.Log("Update setpoint: " + szSetpoint)
                Devices[4].Update(0, szSetpoint)
            except Exception:
                Domoticz.Log("An error occured updating thermostat")
            try:
                szThermostatState = None
                if self.toon.thermostat_info.program_state == 0:
                    #program is off
                    szThermostatState = "Unknown"
                else:
                    try:
                        szThermostatState = str(self.toon.thermostat_state.name)
                    except:
                        Domoticz.Log("An error occured updating thermostat state")

                if szThermostatState:
                    if DEBUG_PRINT:
                        Domoticz.Log("Update state: " + szThermostatState + " - " + str(self.get_scene_value(szThermostatState)))
                    Devices[8].Update(2, str(self.get_scene_value(szThermostatState)))
            except Exception:
                Domoticz.Log("An error occurred updating thermostat state")
            hotwater_on = 0
            heating_on = 0
            preheating_on = 0
            try:
                szBurnerState = self.toon.burner_state
            except Exception:
                szBurnerState = None
                Domoticz.Log("An error occured updating burner state")
            if szBurnerState:
                if DEBUG_PRINT:
                    Domoticz.Log("Update state: " + szBurnerState)
                if szBurnerState == "on":
                    heating_on = 1
                elif szBurnerState == "water_heating":
                    hotwater_on = 1
                elif szBurnerState == "pre_heating":
                    preheating_on = 1
                Devices[5].Update(heating_on, str(heating_on))
                Devices[6].Update(hotwater_on, str(hotwater_on))
                Devices[7].Update(preheating_on, str(preheating_on))

    @staticmethod
    def get_scene_value(value):
        return {'Unknown': 0,
                'Away': 10,
                'Sleep': 20,
                'Home': 30,
                'Comfort': 40}.get(value, 0)


_plugin = BasePlugin()

def onStart():
    _plugin.onStart()

def onStop():
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    _plugin.onCommand(Unit, Command, Level, Hue)

def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)

def onDisconnect(Connection):
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    _plugin.onHeartbeat()

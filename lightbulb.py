import json
from uuid import UUID
from bluepy import btle


class Lightbulb(btle.DefaultDelegate):

  def handleNotification(self, cHandle, value):
    cblen = len(self.__cb_template)
    newstate = {}
    if len(value) == cblen:
      for i in range(cblen):
        tplval = self.__cb_template[i]
        val = value[i]

        if type(tplval) is int or tplval.isnumeric():
          if tplval != val: return
        else:
          if tplval == "pw":
            newstate["state"] = "ON" if val == self.__p_on else "OFF"
          elif tplval == "ef":
            try:
              newstate["effect"] = list(self.__ef_effectlist.keys())[list(self.__ef_effectlist.values()).index(val)]
            except:
              newstate["effect"] = ""
          elif tplval == "es":
            newstate["effect_speed"] = val
          elif tplval in ["r","g","b"]:
            if not "color" in newstate: newstate["color"] = {}
            newstate["color"][tplval] = val
          elif tplval == "wl" and self.__wl_template != None:
            newstate["white_value"] = val

    if "effect" in newstate and newstate["effect"]:
      newstate["color"] = {"r":0, "g":0, "b": 0}
      newstate["white_level"] = 0
      newstate["brightness"] = 255

    else:
      if "color" in newstate:
        color = newstate["color"]
        if "r" in color: r = color["r"]
        else: r = 0
        if "g" in color: g = color["g"]
        else: g = 0
        if "b" in color: b = color["b"]
        else: b = 0
      else:
        r = 0
        g = 0
        b = 0

      max_c = max(r,g,b)

      if max_c == 0:
        newstate["color"] = {"r":255, "g":255, "b": 255}
        if "white_value" in newstate: newstate["brightness"] = newstate["white_value"]
        else: newstate["brightness"] = 0

      else:
        newstate["color"]["r"] = int(r * 255 / max_c)
        newstate["color"]["g"] = int(g * 255 / max_c)
        newstate["color"]["b"] = int(b * 255 / max_c)
        newstate["brightness"] = max_c
        newstate["white_level"] = 0

    self.__state = newstate

#class Lightbulb:

  ##basic entry state
  __state = {
    "state":"UNKNOWN"
  }


  __rgb_template = None
  __wl_template = None
  __ef_template = None


  def __init__(self, settings):
    btle.DefaultDelegate.__init__(self)

    self.__address = settings["address"]
    self.__name = settings["name"]
    self.__device = btle.Peripheral(settings["address"])
    for service in self.__device.getServices():
      print(service)
    self.__p_handle = settings["power"]["handle"]
    self.__p_template = settings["power"]["commandtemplate"]
    self.__p_on = settings["power"]["onval"]
    self.__p_off = settings["power"]["offval"]

    light_safe_name = self.__name.lower().replace(" ","_")
    self.__state_topic = "triones2mqtt/"+ light_safe_name
    self.__command_topic = self.__state_topic + "/set"
    self.__get_topic = self.__state_topic + "/get"

    
    if "rgb" in settings:
      self.__rgb_handle = settings["rgb"]["handle"]
      self.__rgb_template = settings["rgb"]["commandtemplate"]
      self.__state["colour"] = {"r":0, "g": 0, "b": 0}
    
    if "white-level" in settings:
      self.__wl_handle = settings["white-level"]["handle"]
      self.__wl_template = settings["white-level"]["commandtemplate"]
      self.__state["white_level"] = 0

    
    if "effects" in settings:
      self.__ef_handle = settings["effects"]["handle"]
      self.__ef_template = settings["effects"]["commandtemplate"]
      self.__ef_effectlist = settings["effects"]["list"]
      self.__state["effect"] = "none"

    if "query" in settings:
      self.__cb_template = settings["query"]["responsetemplate"]
      #self.__device._callbacks[settings["query"]["responsehandle"]].add(self.__handle_data)
      self.__device.setDelegate(self)
      self.__device.writeCharacteristic(7, bytearray(settings["query"]["command"]))
      self.__device.waitForNotifications(5)


  def setRGB(self, r, g, b):
    if (r == g == b):
      self.setWhite(self.__state["brightness"])
    else:

      self.__state["color"] = {"r":r,"g":g,"b":b}
      self.__state["white_value"] = 0
      self.__state["effect"] = "" 

      br = self.__state["brightness"]

      r = int(r * br / 255)
      g = int(g * br / 255)
      b = int(b * br / 255)


      send = []
      for byte in self.__rgb_template:
        if byte == "r": send.append(r)
        elif byte == "g": send.append(g)
        elif byte == "b": send.append(b)
        else: send.append(byte)
      self.__device.writeCharacteristic(self.__rgb_handle, bytearray(send))


  def setWhite(self, wl):
    self.__state["white_value"] = wl
    self.__state["brightness"] = wl
    self.__state["color"] = {"r":255,"g":255,"b":255}
    self.__state["effect"] = ""

    send = []
    for byte in self.__wl_template:
      if byte == "wl": send.append(wl)
      else: send.append(byte)
    self.__device.writeCharacteristic(self.__wl_handle, bytearray(send))


  def setBrightness(self, br):
    self.__state["brightness"] = br
    if not self.__state["effect"]:
      color = self.__state["color"]
      r = color["r"]
      g = color["g"]
      b = color["b"]
      if r == g == b:
        self.setWhite(br)
      else:
        self.setRGB(r,g,b)


  def setEffect(self, ef):
    self.__state["effect"] = ef
    self.__state["color"] = {"r":0,"g":0,"b":0}
    self.__state["white_value"] = 0
    self.__state["brightness"] = 255

    send = []
    for byte in self.__ef_template:
      if byte == "ef": send.append(self.__ef_effectlist[ef])
      elif byte == "es": send.append(self.__state["effect_speed"])
      else: send.append(byte)
    self.__device.writeCharacteristic(self.__ef_handle, bytearray(send))

  def setEffectSpeed(self, es):
    self.__state["effect_speed"] = es
    if self.__state["effect"]: self.setEffect(self.__state["effect"])

  def turnOff(self):
    if self.__state["state"] != "OFF":
      self.__state["state"] = "OFF"
      send = []
      for byte in self.__p_template:
        if byte == "pw": send.append(self.__p_off)
        else: send.append(byte)
      print(send)
      self.__device.writeCharacteristic(self.__p_handle, bytearray(send))


  def turnOn(self):
    if self.__state["state"] != "ON":
      self.__state["state"] = "ON"
      send = []
      for byte in self.__p_template:
        if byte == "pw": send.append(self.__p_on)
        else: send.append(byte)
      print(send)
      self.__device.writeCharacteristic(self.__p_handle, bytearray(send))


  def toggle(self):
    if self.__state["state"] == "ON":
      self.turnOff()
    else:
      self.turnOn()


  def getStateJSON(self):
    return json.dumps(self.__state)    

  def getCommandTopic(self): return self.__command_topic
  
  def getGetTopic(self): return self.__get_topic

  def getStateTopic(self): return self.__state_topic

  def getHAConfigPath(self):
    return "homeassistant/light/" + self.__name.lower().replace(" ","_") + "/light/config"

  def getHAConfigJSON(self, availability_topic):
    formattedAddr = self.__address.replace(":","")

    haConfig = {
      "schema": "json",
      "command_topic": self.__command_topic,
      "state_topic": self.__state_topic,
      "availability_topic": availability_topic,
      "name": self.__name,
      "unique_id": "triones2mqtt-" + formattedAddr,
      "device": {
        "identifiers": ["triones2mqtt-" + formattedAddr],
        "manufacturer": "Triones",
        "name": self.__name,
      }
    }

    if self.__rgb_template != None: haConfig["rgb"] = True
    if self.__wl_template != None: haConfig["white_value"] = True
    haConfig["brightness"] = haConfig["rgb"] or haConfig["white_value"]

    if self.__ef_template != None:
      haConfig["effect"] = True
      haConfig["effect_list"] = list(self.__ef_effectlist.keys())

    return json.dumps(haConfig)

  def disconnect(self):
    self.__device.disconnect()
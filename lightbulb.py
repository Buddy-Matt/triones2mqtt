import pygatt
import json


class Lightbulb:
  __adapter = None
  __address = None
  __p_handle = None
  __p_on = None
  __p_off = None
  __rgb_handle = None
  __rgb_template = None
  __wl_handle = None
  __wl_template = None

  #TODO: Read the bulb's initial state if possible
  __state = {
    "state":"UNKNOWN",
    "brightness": 0,
    "color": {
      "r": 0,
      "g": 0,
      "b": 0
    },
    "white_value": 0
  }

  def __init__(self, settings):
    self.__adapter = pygatt.GATTToolBackend()
    self.__adapter.start()

    self.__device = self.__adapter.connect(settings["address"])
    self.__p_handle = settings["power"]["handle"]
    self.__p_on = settings["power"]["oncommand"]
    self.__p_off = settings["power"]["offcommand"]

    if "rgb" in settings:
      self.__rgb_handle = settings["rgb"]["handle"]
      self.__rgb_template = settings["rgb"]["commandtemplate"]
    if "white-level" in settings:
      self.__wl_handle = settings["white-level"]["handle"]
      self.__wl_template = settings["white-level"]["commandtemplate"]
    

  def setRGB(self, r, g, b):
    self.__state["color"] = {"r":r,"g":g,"b":b}
    self.__state["white_value"] = 0
    send = []
    for byte in self.__rgb_template:
      if byte == "r": send.append(r)
      elif byte == "g": send.append(g)
      elif byte == "b": send.append(b)
      else: send.append(byte)
    self.__device.char_write_handle(self.__rgb_handle, bytearray(send))

  def setWhite(self, wl):
    self.__state["color"] = {"r":0,"g":0,"b":0}
    self.__state["white_value"] = wl
    send = []
    for byte in self.__wl_template:
      if byte == "wl": send.append(wl)
      else: send.append(byte)
    self.__device.char_write_handle(self.__wl_handle, bytearray(send))

  def turnOff(self):
    self.__state["state"] = "OFF"
    self.__device.char_write_handle(self.__p_handle, bytearray(self.__p_off))

  def turnOn(self):
    self.__state["state"] = "ON"
    self.__device.char_write_handle(self.__p_handle, bytearray(self.__p_on))

  def toggle(self):
    if self.__state["state"] == "ON":
      self.turnOff()
    else:
      self.turnOn()


  def getStateJson(self):
    if self.__state["state"] == "ON":
      return json.dumps(self.__state)    
    else:
      return json.dumps({"state":self.__state["state"]})

  def disconnect(self):
    self.__adapter.stop()
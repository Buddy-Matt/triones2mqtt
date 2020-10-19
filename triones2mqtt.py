#!/bin/python3

import sys
import json
import pygatt
import yaml
import paho.mqtt.client as mqtt


def log(msg):
  print(msg)
  sys.stdout.flush()

def sendState():
  if state["state"] == "ON":
    msg = json.dumps(state)    
  else:
    msg = json.dumps({"state":state["state"]})
    
  log("Sending state " + msg)

  client.publish(state_topic,msg)

def writeRGB(_rgb):
  state["color"] = _rgb
  state["white_value"] = 0
  device.char_write_handle(7, bytearray([0x56,_rgb["r"],_rgb["g"],_rgb["b"],0,0xF0,0xAA]))
  sendState()

def writeWhite(_wv):
  state["color"] = {"r":0,"g":0,"b":0}
  state["white_value"] = _wv
  device.char_write_handle(7, bytearray([0x56,0,0,0,_wv,0x0F,0xAA]))
  sendState()

def writeOff():
  state["state"] = "OFF"
  device.char_write_handle(7, bytearray([0xCC, 0x24, 0x33]))
  sendState()

def writeOn():
  state["state"] = "ON"
  device.char_write_handle(7, bytearray([0xCC, 0x23, 0x33]))
  sendState()
  
def mqtt_message(client, userdasta, message):
  msg = str(message.payload.decode("utf-8"))
  log("Received SET " + msg)
  data = json.loads(msg)
  
  if "color" in data:
    rgb = data["color"]
    writeRGB(rgb)
  if "white_value" in data:
    writeWhite(data["white_value"])
  if "state" in data:
    if data["state"] == "ON":
      writeOn()
    elif data["state"] == "OFF":
      writeOff()
    elif data["state"] == "TOGGLE":
      if state["state"] == "ON":
        writeOff()
      else:
        writeOn()

def mqtt_disconnect(client, userdata, rc):
    if rc != 0:
        log ("MQTT unexpected disconnect. Reconnecting...")


####Read Config
with open("config.yaml","r") as stream:
  try:
    config = yaml.load(stream, Loader=yaml.SafeLoader)
  except:
    log("malformed config file")
    sys.exit()


address = config["address"]
adapter = pygatt.GATTToolBackend()

command_topic = "triones2mqtt/light/set"
state_topic = "triones2mqtt/light"
availability_topic = "triones2mqtt/availability"

if config["homeassistant"] != None:
  haConfig = {
    "white_value": True,
    "rgb": True,
    "schema": "json",
    "command_topic": command_topic,
    "state_topic": state_topic,
    "availability_topic": availability_topic,
    "brightness_scale": 255,
    "name": config["homeassistant"],
    "unique_id": "triones2mqtt-" + address.replace(":",""),
    "device": {
      "identifiers": [
        "triones2mqtt-" + address.replace(":","")
      ],
      "name": "Triones2Mqtt Light",
      "manufacturer": "Triones"
    }
  }

#TODO: Read the bulb's initial state if possible
state = {
  "state":"UNKNOWN",
  "color": {
    "r": 0,
    "g": 0,
    "b": 0
  },
  "white_value": 0
}

adapter.start()
device = None

while device is None:
  try:
    log("Connecting to lightbulb")
    device = adapter.connect(address)
  except:
    log ("Error connecting")
  else:
    log ("Lightbulb connected")

try:
  log ("Connecting to MQTT")
  client = mqtt.Client()
  client.will_set(availability_topic, "offline", 0, True)
  if config["username"] != None and config ["password"] != None:
    client.username_pw_set(config["username"],config["password"])
  client.connect(config["server"])
  log ("MQTT Connected")
  client.subscribe(command_topic)
  client.publish(availability_topic, "online", 0, True)
  if config["homeassistant"] != None:
    client.publish("homeassistant/light/" + config["homeassistant"].replace(" ","").lower() + "/light/config",json.dumps(haConfig),0,True)
  client.on_message=mqtt_message
  client.on_disconnect=mqtt_disconnect
  client.loop_forever()
finally:
  adapter.stop()
  client.publish(availability_topic, "offline", 0, True)
  client.disconnect()
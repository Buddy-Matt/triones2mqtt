#!/bin/python3

import sys
import json
import yaml
import paho.mqtt.client as mqtt

import lightbulb


def log(msg):
  print(msg)
  sys.stdout.flush()


def mqtt_message(client, userdasta, message):
  msg = str(message.payload.decode("utf-8"))
  log("Received SET " + msg)
  data = json.loads(msg)
  if "color" in data:
    rgb = data["color"]
    light.setRGB(rgb["r"],rgb["g"],rgb["b"])
  if "white_value" in data:
    light.setWhite(data["white_value"])
  if "state" in data:
    if data["state"] == "ON":
      light.turnOn()
    elif data["state"] == "OFF":
      light.turnOff()
    elif data["state"] == "TOGGLE":
      light.toggle()
  msg = light.getStateJson()
  client.publish(state_topic,msg)
  log("Sent " + msg)


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

light_safe_name = config["light"]["name"].lower().replace(" ","_")

command_topic = "triones2mqtt/" + light_safe_name + "/set"
state_topic = "triones2mqtt/"+ light_safe_name
availability_topic = "triones2mqtt/availability"

print(command_topic)

if "homeassistant" in config:
  haConfig = {
    "white_value": ("white-level" in config["light"]),
    "rgb": ("rgb" in config["light"]),
    #"brightness": True,
    "schema": "json",
    "command_topic": command_topic,
    "state_topic": state_topic,
    "availability_topic": availability_topic,
    "brightness_scale": 255,
    "name": config["light"]["name"],
    "unique_id": "triones2mqtt-" + config["light"]["address"].replace(":",""),
    "device": {
      "identifiers": [
        "triones2mqtt-" + config["light"]["address"].replace(":","")
      ],
      "name": config["light"]["name"],
      "manufacturer": "Triones"
    }
  }




light = None

while light is None:
  try:
    log("Connecting to lightbulb")
    light = lightbulb.Lightbulb(config["light"])
  except:
    log ("Error connecting")
  else:
    log ("Lightbulb connected")

try:
  log ("Connecting to MQTT")
  client = mqtt.Client()
  client.will_set(availability_topic, "offline", 0, True)
  if config["mqtt"]["username"] != None and config["mqtt"]["password"] != None:
    client.username_pw_set(config["mqtt"]["username"],config["mqtt"]["password"])
  client.connect(config["mqtt"]["server"])
  log ("MQTT Connected")
  client.subscribe(command_topic)
  client.publish(availability_topic, "online", 0, True)
  if "homeassistant" in config: client.publish("homeassistant/light/" + light_safe_name + "/light/config",json.dumps(haConfig),0,True)
  client.on_message=mqtt_message
  client.on_disconnect=mqtt_disconnect
  client.loop_forever()
finally:
  light.disconnect()
  client.publish(availability_topic, "offline", 0, True)
  client.disconnect()
#!/bin/python3

import sys
import json
import yaml
import paho.mqtt.client as mqtt

import lightbulb


def log(msg):
  print(msg)
  sys.stdout.flush()


def mqtt_message(client, userdata, message):
  msg = str(message.payload.decode("utf-8"))

  if message.topic == "homeassistant/status":
    if msg != "online": return

  else:
    log("Received SET " + msg)
    data = json.loads(msg)

    if "color" in data:
      rgb = data["color"]
      light.setRGB(rgb["r"],rgb["g"],rgb["b"])
    elif "white_value" in data:
      light.setWhite(data["white_value"])
    elif "effect" in data:
      light.setEffect(data["effect"])
    
    if "brightness" in data:
      light.setBrightness(data["brightness"])

    if "effect_speed" in data:
      light.setEffectSpeed(data["effect_speed"])
    
    if "state" in data:
      if data["state"] == "ON":
        light.turnOn()
      elif data["state"] == "OFF":
        light.turnOff()
      elif data["state"] == "TOGGLE":
        light.toggle()

  msg = light.getStateJSON()
  client.publish(light.getStateTopic(),msg)
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

availability_topic = "triones2mqtt/availability"

light = None

#/while light is None:
#try:
log("Connecting to lightbulb")
light = lightbulb.Lightbulb(config["light"])
log ("Lightbulb connected")

#except Exception as e:
#  log ("Error connecting")
#  log (str(e))
#  exit
#else:

try:
  log ("Connecting to MQTT")
  client = mqtt.Client()
  client.will_set(availability_topic, "offline", 0, True)
  if config["mqtt"]["username"] != None and config["mqtt"]["password"] != None:
    client.username_pw_set(config["mqtt"]["username"],config["mqtt"]["password"])
  client.connect(config["mqtt"]["server"])
  log ("MQTT Connected")

  msg = light.getStateJSON()
  client.publish(light.getStateTopic(),msg)
  log("Sent " + msg)

  client.subscribe(light.getCommandTopic())
  client.publish(availability_topic, "online", 0, True)
  if "homeassistant" in config:
    client.publish(light.getHAConfigPath(),light.getHAConfigJSON(availability_topic),0,True)
    client.subscribe("homeassistant/status")

  client.on_message=mqtt_message
  client.on_disconnect=mqtt_disconnect

  client.loop_forever()

finally:
  light.disconnect()
  client.publish(availability_topic, "offline", 0, True)
  client.disconnect()
#!/bin/python3

import sys
import json
import yaml
import asyncio_mqtt as mqtt
import asyncio
loop = asyncio.get_event_loop()

import lightbulb


class Triones2Mqtt:

  def log(self,msg):
    print(msg)
    sys.stdout.flush()

  async def __aenter__(self):
      print('Starting Triones2Mqtt')
      return self

  async def __aexit__(self, *_):
      print("Shutting down")
      if hasattr(self,"light") and self.light is not None:
        await self.light.disconnect()

      
      
  async def mqtt_message(self,message):
    msg = str(message.payload.decode("utf-8"))

    if message.topic == "homeassistant/status":
      if msg != "online": return

    elif not message.topic.endswith("/get") :
      self.log("Received SET " + msg)
      data = json.loads(msg)

      if "color" in data:
        rgb = data["color"]
        await self.light.setRGB(rgb["r"],rgb["g"],rgb["b"])
      elif "white_value" in data:
        await self.light.setWhite(data["white_value"])
      elif "effect" in data:
        await self.light.setEffect(data["effect"])
      
      if "brightness" in data:
        await self.light.setBrightness(data["brightness"])

      if "effect_speed" in data:
        await self.light.setEffectSpeed(data["effect_speed"])
      
      if "state" in data:
        if data["state"] == "ON":
          await self.light.turnOn()
        elif data["state"] == "OFF":
          await self.light.turnOff()
        elif data["state"] == "TOGGLE":
          await self.light.toggle()

    msg = self.light.getStateJSON()
    self.client.publish(self.light.getStateTopic(),msg)
    self.log("Sent " + msg)


  async def Listen(self):
    ####Read Config
    with open("config.yaml","r") as stream:
      try:
        config = yaml.load(stream, Loader=yaml.SafeLoader)
      except:
        self.log("malformed config file")
        sys.exit()

    self.availability_topic = "triones2mqtt/availability"

    self.light = None

    #/while light is None:
    #try:
    self.log("Connecting to lightbulb")
    self.light = lightbulb.Lightbulb(config["light"])
    await self.light.connect()
    self.log ("Lightbulb connected")

    #except Exception as e:
    #  log ("Error connecting")
    #  log (str(e))
    #  exit
    #else:

    while True:
      try:
        self.log ("Connecting to MQTT")

        async with mqtt.Client(
          hostname = config["mqtt"]["server"],
          username = config["mqtt"]["username"],
          password = config["mqtt"]["password"],
          will = mqtt.Will(self.availability_topic,"offline", retain = True)) as self.client:
          self.log ("MQTT Connected")

          async with self.client.unfiltered_messages() as messages:
            msg = self.light.getStateJSON()
            await self.client.publish(self.light.getStateTopic(),msg)
            self.log("Sent " + msg)

            await self.client.subscribe(self.light.getCommandTopic())
            await self.client.subscribe(self.light.getGetTopic())
            await self.client.publish(self.availability_topic, "online", 0, True)

            if "homeassistant" in config:
              await self.client.publish(self.light.getHAConfigPath(),self.light.getHAConfigJSON(self.availability_topic),0,True)
              await self.client.subscribe("homeassistant/status")

            async for message in messages:
              await self.mqtt_message(message)
        
      except mqtt.MqttError as error:
        self.log ("MQTT unexpected disconnect. Reconnecting...")
      finally:
          await asyncio.sleep(1)



async def main():
    async with Triones2Mqtt() as t2m:
        await t2m.Listen()

asyncio.run(main())
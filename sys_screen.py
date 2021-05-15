#!/home/pi/.env/bin/python

import argparse, sys, os, time, logging, curses, json
import paho.mqtt.client as mqtt
from queue import Queue
import asyncio, os
from evdev import InputDevice, categorize, ecodes

class setCursor:
  def __init__(self):
    pass
  def on(self):
    os.system('setterm -cursor on')
  def off(self):
    os.system('setterm -cursor off')

class backLightSwitch:
  def __init__(self, status, blight):
    self.duration = blight
    self.status = False
    if status == True:
      asyncio.create_task(self.on())
  async def on(self):
    if self.status == False:
      self.status = True
      os.system('echo 0 > /sys/class/backlight/fb_s6d02a1/bl_power')
      await asyncio.sleep(self.duration)
      os.system('echo 1 > /sys/class/backlight/fb_s6d02a1/bl_power')
      self.status = False
        
async def switch_light(blight):
  dev = InputDevice('/dev/input/event0')  
  print(dev)
  sw = backLightSwitch(True, blight)
  while True:
    event = await dev.async_read_one()
    if event.type == ecodes.EV_KEY and event.value == 0:
      asyncio.create_task(sw.on())

def screen_clear():
  # for windows
  if os.name == 'nt':
    _ = os.system('cls')
  # for mac and linux(here, os.name is 'posix')
  else:
    _ = os.system('clear')

def on_connect(client, userdata, flags, rc):
  if rc == 0:
    logging.info(f'Connected success with code {rc}')
    client.subscribe('stats/#',qos=0)
  else:
    logging.info(f'Connected fail with code {rc}')

def on_message(client, userdata, message):
  q.put(message)
  
async def show_stats(polling):
  host_stats = {}
  ups_stats = {}

  while True:
    while not q.empty():
      message = q.get()
      if message is None:
  	    continue
      if message.topic == "stats/host": 
        items = json.loads(message.payload.decode("utf-8"))
        host_stats[items['ID']] = items
      if message.topic == "stats/ups":
        items = json.loads(message.payload.decode("utf-8"))
        ups_stats[items['ID']] = items

    host_ids = list(host_stats.keys())
    ups_ids = list(ups_stats.keys())
    host_ids.sort()
    ups_ids.sort()
    
    screen_clear()
    for i in host_ids:
      print(f"{'host:' + str(host_stats[i]['NODE']) : <14}{str(host_stats[i]['TIME']) : >25}")
      print(f"{'load:' + str(host_stats[i]['CPU']) + '%' : <13}{'temp:' + str(host_stats[i]['TEMPERATURE']) + chr(176) + 'C' : ^14}")
      print(f"{'mem:' + str(host_stats[i]['MEMORY.TOTAL']) + 'MB' : <13}{'avail:' + str(host_stats[i]['MEMORY.AVAIL']) + 'MB' : ^14}{'used:' + str(host_stats[i]['MEMORY.PCT']) + '%' : >12}")
      print(f"{'disk:' + str(host_stats[i]['DISK.TOTAL']) + 'MB' : <13}{'free:' + str(host_stats[i]['DISK.FREE']) + 'MB' : ^14}{'used:' + str(host_stats[i]['DISK.PCT']) + '%' : >12}")
      print()
    for i in ups_ids:
      print(f"{'host:' + str(ups_stats[i]['UPSNAME']) : <14}{str(ups_stats[i]['DATE']) : >25}")
      print(f"{'status:' + str(ups_stats[i]['STATUS']) : <19}{'line:' + str(ups_stats[i]['LINEV']) + 'V' : >20}")
      print(f"{'charge:' + str(ups_stats[i]['BCHARGE']) + '%' : <13}{'load:' + str(ups_stats[i]['LOADPCT']) + '%' : ^13}{'tleft:' + str(ups_stats[i]['TIMELEFT']) + 'm' : >13}")
      print(f"{'batt:' + str(ups_stats[i]['BATTV']) + 'V' : <13}{'xfers:' + str(ups_stats[i]['NUMXFERS']) : ^13}{'t_on_batt:' + str(ups_stats[i]['TONBATT']) + 's' : >13}")
      print(f"{'last_xfer:' + str(ups_stats[i]['XOFFBATT']) : <14}{'c_on_batt:' + str(ups_stats[i]['CUMONBATT']) + 's' : >25}", end="\r")

    await asyncio.sleep(polling)
      
def main(args):
  # main function
  broker = args['broker']
  polling = int(args['polling'])
  blight = int(args['blight'])

  logging.basicConfig(filename = 'events.log', level = logging.INFO, format = '%(asctime)s %(message)s')

  cursor = setCursor()

  try:
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.will_set('node/status', '{"status": "Off"}')
    mqtt_client.connect(broker, 1883, 60)
    mqtt_client.loop_start()
    
    cursor.off()
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(show_stats(polling))
    asyncio.ensure_future(switch_light(blight))
    loop.run_forever()

  except KeyboardInterrupt:
    print('_process killed')

  finally:
    cursor.on()
    screen_clear()
    mqtt_client.disconnect()
    mqtt_client.loop_stop()
    loop.stop()
    loop.close()

if __name__ == '__main__':
  q = Queue()
  # Construct the argument parser
  ap = argparse.ArgumentParser(
    prog='sys_screen',
    usage='%(prog)s [options]',
    description='Collect the Status from host.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  # Add the arguments to the parser
  ap.add_argument('-b', '--broker', required=True, help='mqtt broker')
  ap.add_argument('-p', '--polling', default='20', type=int, required=False, help='interval to screen in sec')
  ap.add_argument('-l', '--blight', default='30', type=int, required=False, help='backlight "ON" in sec')
  ap.add_argument('-v', '--version', action='version', version='%(prog)s 1.0', help='show version')
  args = vars(ap.parse_args())
  main(args)
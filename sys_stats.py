#!/home/pi/.env/bin/python

# env_collect.py
# collect enviroment variables and send via mqtt (mosquitto)
import argparse, sys, socket, logging, time, json
import psutil
import paho.mqtt.client as mqtt
from gpiozero import CPUTemperature
from apcaccess import status as apc

class Stats:
  def __init__(self):
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load = psutil.cpu_percent()
    cpu = CPUTemperature()
  
    self.mem_avail = memory.available >> 20
    self.mem_total = memory.total >> 20
    self.mem_percent = memory.percent
  
    self.disk_free = disk.free >> 30
    self.disk_total = disk.total >> 30
    self.disk_percent = disk.percent
  
    self.cpu_load = load
  
    self.cpu_temp = round(cpu.temperature,1)

class Apc:
  def __init__(self, address):
    apcups = apc.get(host=address)
    self.status = apc.parse(apcups, strip_units=True)
  
def hostname():
  return socket.gethostname()

def host_stats(id):
  status = Stats()
  stats = {}
  stats["ID"] = id 
  stats["TIME"] = time.strftime(' %Y-%m-%d %H:%M:%S',time.localtime())
  stats["NODE"] = hostname()
  stats['CPU'] = status.cpu_load
  stats['MEMORY.AVAIL'] = status.mem_avail
  stats['MEMORY.TOTAL'] = status.mem_total
  stats['MEMORY.PCT'] = status.mem_percent
  stats['DISK.FREE'] = status.disk_free
  stats['DISK.TOTAL'] = status.disk_total
  stats['DISK.PCT'] = status.disk_percent
  stats['TEMPERATURE'] = status.cpu_temp
  return json.dumps(stats)

def ups_stats(id):
  stats = {}
  ups = Apc('192.168.1.10')
  ups.status["ID"] = id
  ups.status["DATE"] = ups.status["DATE"][:-6] 
  return json.dumps(ups.status)

def on_connect(client, userdata, flags, rc):
  if rc == 0:
    logging.info(f'Connected success with code {rc}')
  else:
    logging.info(f'Connected fail with code {rc}')

def main(args):
  # main function
  logging.basicConfig(filename = 'events.log', level = logging.INFO, format = '%(asctime)s %(message)s')
  mqtt_broker = args['broker'] 

  host_topic = "stats/host"
  host_client = mqtt.Client()
  host_client.on_connect = on_connect
  host_client.connect(mqtt_broker, 1883, 60)
  host_client.loop_start()

  ups_topic = "stats/ups"
  ups_client = mqtt.Client()
  ups_client.on_connect = on_connect
  ups_client.connect(mqtt_broker, 1883, 60)
  ups_client.loop_start()

  try:
    while True:
      status = host_stats(args['id'])
      host_client.publish(topic = host_topic, payload = status, qos = 0, retain = False)
      if args['stats'] == 'u':
        status = ups_stats(args['id'])
        ups_client.publish(topic = ups_topic, payload = status, qos = 0, retain = False)
      time.sleep(int(args['polling']))
  except KeyboardInterrupt:
    print(" process killed")
  finally:
    host_client.disconnect()
    host_client.loop_stop()
    ups_client.disconnect()
    ups_client.loop_stop()
    
    
if __name__ == "__main__":
  # Construct the argument parser
  ap = argparse.ArgumentParser()
  # Add the arguments to the parser
  ap.add_argument("-b", "--broker", required=True, help="mqtt broker fqdn or ip address")
  ap.add_argument("-i", "--id", required=True, help="instance id#")
  ap.add_argument("-p", "--polling", required=True, help="polling interval in seconds to collect stats")
  ap.add_argument("-s", "--stats", required=False, help="collect also status from ups [u]")
  args = vars(ap.parse_args())
  main(args)
parser.add_argument('--bar', action='store_false')
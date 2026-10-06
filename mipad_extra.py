import glob
import paho.mqtt.client as mqtt
import time

broker = '192.168.1.100'   # IP deines MQTT-Brokers
port = 1883
topic_prefix = 'mipad/extra'

# Zonenname -> (MQTT-Topic, Nachkommastellen)
# Zonennamen sind geraeteabhaengig, siehe README
ZONES = {
    'gpuss-0':         ('gpu_temperature', 1),
    'quiet_therm':     ('quiet_temperature', 1),
    'sys-therm-0':     ('sys_temperature', 1),
    'flash_therm':     ('flash_temperature', 1),
    'backlight_therm': ('backlight_temperature', 1),
    'vbat':            ('battery_voltage', 3),
}

def read_thermal(zone_name):
    """Liest eine Thermal-Zone per Name, Rohwert geteilt durch 1000 (oder None)."""
    for type_file in glob.glob('/sys/class/thermal/thermal_zone*/type'):
        try:
            with open(type_file) as f:
                if f.read().strip() != zone_name:
                    continue
            with open(type_file.replace('/type', '/temp')) as f:
                value = int(f.read().strip()) / 1000
            if value < -30:  # nicht belegte Sensoren
                return None
            return value
        except Exception:
            return None
    return None

def send_extra_info():
    values = {}
    for zone, (topic, decimals) in ZONES.items():
        value = read_thermal(zone)
        if value is not None:
            values[topic] = round(value, decimals)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(broker, port, 60)
        for topic, value in values.items():
            client.publish(f'{topic_prefix}/{topic}', str(value))
        client.disconnect()
        print("Daten gesendet:", values)
    except Exception as e:
        print("Fehler bei MQTT-Verbindung:", e)

if __name__ == "__main__":
    while True:
        send_extra_info()
        time.sleep(60)

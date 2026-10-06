import subprocess
import json
import glob
import paho.mqtt.client as mqtt
import time

broker = '192.168.1.100'   # IP deines MQTT-Brokers
port = 1883
topic_prefix = 'mipad'     # Name deines Geraets im MQTT-Baum

def format_value(value, max_chars=4):
    s = f"{value:.4g}"  # 4 signifikante Stellen
    if len(s) > max_chars:
        s = s[:max_chars]
    return s

def read_thermal(zone_name):
    """Liest eine Thermal-Zone per Name und gibt Grad Celsius zurueck (oder None)."""
    for type_file in glob.glob('/sys/class/thermal/thermal_zone*/type'):
        try:
            with open(type_file) as f:
                if f.read().strip() != zone_name:
                    continue
            with open(type_file.replace('/type', '/temp')) as f:
                value = int(f.read().strip()) / 1000
            if value < -30:  # nicht belegte Sensoren (-40.96 usw.)
                return None
            return value
        except Exception:
            return None
    return None

def send_battery_info():
    battery_json = subprocess.check_output(['termux-battery-status'])
    battery = json.loads(battery_json)

    # Strom: positiv = Akku wird entladen (Verbrauch), negativ = Akku wird geladen
    current_uA = battery.get('current', 0)
    current_mA = round((-current_uA) / 1000)

    # Leistung in Watt = Strom (A) * Spannung (V), Spannung kommt in mV
    voltage_mV = battery.get('voltage', 0)
    power_W = round((current_mA / 1000) * (voltage_mV / 1000), 2)

    temperature = battery.get('temperature', 0)
    percentage = battery.get('percentage', 0)
    cycle = battery.get('cycle')

    formatted_values = {
        'health': battery.get('health', 'unbekannt'),
        'percentage': format_value(percentage),
        'plugged': battery.get('plugged', 'unbekannt'),
        'status': battery.get('status', 'unbekannt'),
        'temperature': format_value(temperature),
        'current_mA': current_mA,
        'power_W': power_W
    }

    # Zonennamen sind geraeteabhaengig, siehe README
    cpu_temp = read_thermal('cpuss-0')
    charger_temp = read_thermal('charger_therm')

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    try:
        client.connect(broker, port, 60)

        client.publish(f'{topic_prefix}/battery_level', str(formatted_values['percentage']))
        client.publish(f'{topic_prefix}/battery_temperature', str(formatted_values['temperature']))

        client.publish(f'{topic_prefix}/battery_health', str(formatted_values['health']))
        client.publish(f'{topic_prefix}/battery_plugged', str(formatted_values['plugged']))
        client.publish(f'{topic_prefix}/battery_status', str(formatted_values['status']))
        client.publish(f'{topic_prefix}/battery_current_mA', str(formatted_values['current_mA']))
        client.publish(f'{topic_prefix}/battery_power_W', str(formatted_values['power_W']))

        if cycle is not None:
            client.publish(f'{topic_prefix}/battery_cycle', str(cycle))
            formatted_values['cycle'] = cycle

        if cpu_temp is not None:
            client.publish(f'{topic_prefix}/cpu_temperature', format_value(cpu_temp))
            formatted_values['cpu_temperature'] = format_value(cpu_temp)
        if charger_temp is not None:
            client.publish(f'{topic_prefix}/charger_temperature', format_value(charger_temp))
            formatted_values['charger_temperature'] = format_value(charger_temp)

        client.disconnect()

        print("Daten gesendet:", formatted_values)
    except Exception as e:
        print("Fehler bei MQTT-Verbindung:", e)

if __name__ == "__main__":
    while True:
        send_battery_info()
        time.sleep(30)

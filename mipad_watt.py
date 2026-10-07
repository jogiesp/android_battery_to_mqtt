# EXPERIMENTELL: Wie mipad.py, zusaetzlich Strom (mA) und Leistung (Watt).
# Die Werte sind noch nicht genau (siehe README). Nicht zusammen mit mipad.py starten,
# beide Skripte senden an dieselben Topics.
import subprocess
import json
import glob
import paho.mqtt.client as mqtt
import time

broker = '192.168.1.100'   # IP deines MQTT-Brokers
port = 1883
topic_prefix = 'mipad'     # Name deines Geraets im MQTT-Baum

AVG_WINDOW_S = 600         # Zeitfenster fuer den Durchschnittswert (10 Minuten)
AVG_MIN_AGE_S = 300        # erst senden, wenn mindestens 5 Minuten Daten da sind

history = []               # Liste von (Zeitstempel, charge_counter in uAh, Spannung in mV)
last_plugged = None

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

def update_average(battery):
    """Berechnet Strom und Leistung als Durchschnitt aus der Aenderung des
    charge_counter ueber das Zeitfenster. Negativ = Verbrauch, positiv = Laden.
    Gibt (mA, Watt) zurueck oder None, solange noch zu wenig Daten da sind."""
    global history, last_plugged

    now = time.time()
    plugged = battery.get('plugged')
    charge = battery.get('charge_counter')
    voltage = battery.get('voltage', 0)

    # Beim Ein- oder Ausstecken des Ladekabels neu anfangen
    if plugged != last_plugged:
        history = []
        last_plugged = plugged

    if charge is None:
        return None

    history.append((now, charge, voltage))

    # Alte Eintraege entfernen, aber den aeltesten innerhalb des Fensters behalten
    while len(history) > 1 and now - history[1][0] >= AVG_WINDOW_S:
        history.pop(0)

    t0, charge0, _ = history[0]
    dt = now - t0
    if dt < AVG_MIN_AGE_S:
        return None

    avg_mA = (charge - charge0) / 1000 / (dt / 3600)
    avg_V = sum(v for _, _, v in history) / len(history) / 1000
    return round(avg_mA), round(avg_mA / 1000 * avg_V, 2)

def send_battery_info():
    battery_json = subprocess.check_output(['termux-battery-status'])
    battery = json.loads(battery_json)

    # Strom wie in der App Ampere: negativ = Akku wird entladen (Verbrauch), positiv = Akku wird geladen
    current_uA = battery.get('current', 0)
    current_mA = round(current_uA / 1000)

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

    average = update_average(battery)

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

        if average is not None:
            avg_mA, avg_W = average
            client.publish(f'{topic_prefix}/battery_current_avg_mA', str(avg_mA))
            client.publish(f'{topic_prefix}/battery_power_avg_W', str(avg_W))
            formatted_values['current_avg_mA'] = avg_mA
            formatted_values['power_avg_W'] = avg_W

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

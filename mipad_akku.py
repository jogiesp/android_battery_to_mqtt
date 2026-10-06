import subprocess
import json
import paho.mqtt.client as mqtt

broker = '192.168.1.100'   # IP deines MQTT-Brokers
port = 1883
topic_prefix = 'mipad/extra'

CAPACITY_MAH = 12000        # Akku-Kapazitaet in mAh
NOMINAL_VOLTAGE = 3.85      # Nennspannung in Volt (Li-Poly)
CHARGE_EFFICIENCY = 0.85    # Ladewirkungsgrad (0.80 bis 0.90 ueblich)

def main():
    battery = json.loads(subprocess.check_output(['termux-battery-status']))
    cycles = battery.get('cycle')
    if cycles is None:
        print("Kein Zykluswert von termux-battery-status erhalten.")
        return

    throughput_ah = cycles * CAPACITY_MAH / 1000
    battery_kwh = throughput_ah * NOMINAL_VOLTAGE / 1000
    grid_kwh = battery_kwh / CHARGE_EFFICIENCY
    loss_kwh = grid_kwh - battery_kwh

    values = {
        'battery_cycles_used': cycles,
        'battery_throughput_Ah': round(throughput_ah, 2),
        'battery_energy_kWh': round(battery_kwh, 3),
        'battery_grid_energy_kWh': round(grid_kwh, 3),
        'battery_charge_loss_kWh': round(loss_kwh, 3),
    }

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
    main()

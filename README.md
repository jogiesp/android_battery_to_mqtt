# 📱 mipad – Tablet-Akku & Temperaturen per MQTT

Kleine Python-Skripte, die auf einem **Android-Tablet oder -Handy mit Termux** laufen und Akku- und Temperaturdaten per **MQTT** an dein Smart Home schicken (ioBroker, Home Assistant, Node-RED, Grafana …).

Entwickelt und getestet auf einem **Xiaomi Redmi Pad 2**. 🚀

---

## ✨ Was kann das?

- 🔋 Akkustand, Zustand, Ladestatus und Temperatur
- ⚡ Aktueller Strom (mA) und **Leistung in Watt**
- 🔁 **Ladezyklen** des Akkus, um die Alterung über Monate zu beobachten
- 🌡️ CPU-, GPU-, Lade- und Gehäusetemperaturen
- 🧮 Abschätzung, wie viel Energie der Akku bisher durchgesetzt hat, **inklusive Ladeverlusten**
- 🏠 Läuft im Hintergrund in Termux (mit tmux und Wake-Lock), ohne Root

---

## 📦 Die Skripte

| Datei | Zweck | Läuft |
|---|---|---|
| `mipad.py` | Hauptskript: Akku, Strom, Watt, Zyklen, CPU- und Ladetemperatur | 🔁 dauerhaft, alle 30 s |
| `mipad_extra.py` | Zusatzwerte: GPU, Gehäuse, Speicher, Backlight, Akkuspannung | 🔁 optional, alle 60 s |
| `mipad_akku.py` | Schätzt den bisherigen Energiedurchsatz des Akkus | 1️⃣ einmalig, nur bei Bedarf |

---

## 🧰 Voraussetzungen

- 📲 Ein Android-Gerät
- 🖥️ **Termux** (am besten von **F-Droid** oder **GitHub**, nicht aus dem Play Store, dort ist die Version veraltet)
- 🔌 **Termux:API** (die App, ebenfalls aus derselben Quelle wie Termux)
- 📡 Ein **MQTT-Broker** im Netzwerk, z. B. Mosquitto oder der MQTT-Adapter von ioBroker

> ⚠️ Termux und Termux:API müssen aus **derselben Quelle** stammen (beide F-Droid oder beide GitHub), sonst funktioniert die Verbindung nicht.

---

## 🛠️ Installation

### 1️⃣ Termux und Termux:API installieren

Beide Apps von F-Droid oder GitHub herunterladen und installieren. Danach Termux einmal öffnen.

### 2️⃣ Pakete installieren

```bash
pkg update
pkg install python termux-api tmux
pip install paho-mqtt
```

| Paket | Wofür |
|---|---|
| `python` | Ausführen der Skripte |
| `termux-api` | Zugriff auf die Akkudaten (`termux-battery-status`) |
| `tmux` | Optional: Sitzung, die weiterläuft, wenn du das Termux-Fenster schließt |
| `paho-mqtt` | MQTT-Verbindung (Version 2.x wird benötigt) |

### 3️⃣ Akku-Abfrage testen

```bash
termux-battery-status
```

Du solltest einen JSON-Block mit `percentage`, `temperature`, `current` usw. sehen. Kommt nichts, fehlt die Termux:API-App oder ihre Berechtigung.

### 4️⃣ Skripte herunterladen

```bash
pkg install git
git clone https://github.com/jogiesp/android_battery_to_mqtt.git
cd android_battery_to_mqtt
```

---

## ⚙️ Konfiguration

Am Anfang jedes Skripts stehen die Einstellungen:

```python
broker = '192.168.1.100'   # IP deines MQTT-Brokers
port = 1883
topic_prefix = 'mipad'     # Name deines Geräts im MQTT-Baum
```

Wenn du mehrere Geräte hast, gib jedem einen eigenen `topic_prefix`, damit sich die Werte nicht vermischen.

Bei `mipad_akku.py` zusätzlich:

```python
CAPACITY_MAH = 12000        # Akku-Kapazität deines Geräts
NOMINAL_VOLTAGE = 3.85      # Nennspannung (Li-Poly)
CHARGE_EFFICIENCY = 0.85    # Ladewirkungsgrad, üblich 0.80 bis 0.90
```

---

## ▶️ Starten

### Zum Testen

```bash
python mipad.py
```

Alle 30 Sekunden erscheint eine Zeile mit `Daten gesendet: ...`. Mit `Strg+C` stoppst du es.

### Dauerhaft im Hintergrund

**Termux** ist die App, **tmux** ist ein kleines Zusatzprogramm *innerhalb* von Termux (wird mit `pkg install tmux` nachinstalliert). Mit tmux läuft das Skript weiter, wenn du das Termux-Fenster schließt oder zur Startseite wechselst.

> ⚠️ Es läuft aber nur so lange, wie Android die **Termux-App selbst** am Leben lässt. Wird Termux vom System beendet, ist tmux mit allem darin ebenfalls weg.

So gibst du Termux die besten Chancen:

1. 🔒 **Wake-Lock aktivieren:** In der Termux-Benachrichtigung auf *Acquire wakelock* tippen oder im Terminal `termux-wake-lock` ausführen
2. 🔋 **Akku-Optimierung für Termux ausschalten:** Android-Einstellungen, Apps, Termux, Akku, dann "Keine Einschränkungen" bzw. "Nicht optimieren" (Name je nach Hersteller verschieden)
3. 👆 Termux bei manchen Herstellern **nicht aus der Liste der zuletzt benutzten Apps wegwischen**

Starten in tmux:

```bash
tmux new -s mipad
python mipad.py
```

Dann mit `Strg+B` und danach `D` aus dem Fenster lösen, das Skript läuft weiter. Zurück ins Fenster geht es mit:

```bash
tmux attach -t mipad
```

Nach einem **Neustart des Geräts** muss das Skript von Hand wieder gestartet werden (oder du richtest dafür die App *Termux:Boot* ein).

---

## 📊 Gesendete Daten

### `mipad.py` → `mipad/...`

| Topic | Bedeutung | Einheit |
|---|---|---|
| `battery_level` | Akkustand | % |
| `battery_temperature` | Akkutemperatur | °C |
| `battery_health` | Zustand laut Android (z. B. `GOOD`) | Text |
| `battery_plugged` | Ladekabel (`PLUGGED_AC`, `UNPLUGGED` …) | Text |
| `battery_status` | `CHARGING`, `DISCHARGING`, `FULL` … | Text |
| `battery_current_mA` | Akkustrom, **positiv = Verbrauch, negativ = Laden** | mA |
| `battery_power_W` | Aktuelle Leistung (Strom × Spannung) | W |
| `battery_cycle` | Ladezyklen des Akkus | Anzahl |
| `cpu_temperature` | CPU-Subsystem | °C |
| `charger_temperature` | Ladebereich | °C |

### `mipad_extra.py` → `mipad/extra/...`

| Topic | Bedeutung | Einheit |
|---|---|---|
| `gpu_temperature` | Grafikeinheit | °C |
| `quiet_temperature` | Sensor nahe der Oberfläche | °C |
| `sys_temperature` | Systemsensor | °C |
| `flash_temperature` | Speicher | °C |
| `backlight_temperature` | Hintergrundbeleuchtung | °C |
| `battery_voltage` | Akkuspannung | V |

### `mipad_akku.py` → `mipad/extra/...`

| Topic | Bedeutung | Einheit |
|---|---|---|
| `battery_cycles_used` | Bisherige Ladezyklen | Anzahl |
| `battery_throughput_Ah` | Geschätzter Gesamtdurchsatz (Zyklen × Kapazität) | Ah |
| `battery_energy_kWh` | Energie, die durch den Akku geflossen ist | kWh |
| `battery_grid_energy_kWh` | Entsprechende Energie aus der Steckdose (inkl. Ladeverlust) | kWh |
| `battery_charge_loss_kWh` | Geschätzter Ladeverlust | kWh |

> 🧮 Die Werte von `mipad_akku.py` sind eine **Abschätzung**, kein Messwert. Der Zykluszähler zählt ganze Zahlen, deshalb ist das Ergebnis am Anfang noch grob und wird mit der Zeit genauer.

---

## 🌡️ Anderes Gerät? Temperatur-Zonen anpassen

Die Namen der Temperatursensoren (`cpuss-0`, `charger_therm` usw.) sind **geräteabhängig**. Auf deinem Gerät können sie anders heißen oder gesperrt sein. So findest du heraus, was dein Gerät anbietet:

```bash
paste <(cat /sys/class/thermal/thermal_zone*/type) <(cat /sys/class/thermal/thermal_zone*/temp)
```

Die Werte stehen in Millicelsius (`34500` = 34,5 °C). Zonen mit `0` oder `-40960` sind nicht belegt. Trage die passenden Namen in `read_thermal(...)` in `mipad.py` bzw. in der Liste `ZONES` in `mipad_extra.py` ein.

Auch `battery_cycle` hängt vom Gerät ab: Nicht jedes Gerät liefert das Feld `cycle` in `termux-battery-status`. Fehlt es, wird der Wert einfach nicht gesendet.

---

## 🏠 Tipp für ioBroker / Datenbank

- 🗄️ Nicht jeden Wert in die History aufnehmen. Für den Alltag reichen `battery_level` und `battery_status`.
- 🔁 `battery_cycle` am besten mit "bei Änderung" aufzeichnen, er ändert sich nur alle paar Tage.
- 🧹 ioBroker legt für jedes neue Topic dauerhaft ein Objekt an. Alte Topics nach Umbenennungen von Hand löschen.

---

## 🩺 Probleme?

| Problem | Lösung |
|---|---|
| `termux-battery-status` hängt oder bleibt leer | Termux:API-App installieren, beide Apps aus derselben Quelle |
| `ModuleNotFoundError: No module named 'paho'` | `pip install paho-mqtt` |
| `python: not found` | `pkg install python` |
| `Fehler bei MQTT-Verbindung` | Broker-IP und Port prüfen, läuft der Broker, ist er im Netz erreichbar? |
| Skript stoppt im Hintergrund | In `tmux` starten, Wake-Lock aktivieren, Akku-Optimierung für Termux ausschalten (siehe *Dauerhaft im Hintergrund*) |

---

## 📄 Lizenz

MIT-Lizenz. Mach damit, was du willst. 🎉

---

## 🤝 Mitmachen

Du hast das Skript auf einem anderen Gerät getestet? Dann freue ich mich über einen **Issue** oder **Pull Request** mit den passenden Sensornamen. ⭐ Wenn dir das Projekt gefällt, lass gern einen Stern da.

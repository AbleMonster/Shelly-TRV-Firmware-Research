# Shelly TRV Gen1 Battery Logger

## Funktion

- fragt alle Geräte zu festen Zeitrastern ab
- `/status` und `/debug/log` bei allen Firmware-Versionen
- `/stats` ausschließlich bei erkannter Firmware `2.2.4`
- speichert alle Rohantworten in SQLite
- erzeugt täglich einen PDF-Bericht über exakt 24 Stunden
- Standard:
  - Messung alle 30 Minuten
  - Bericht täglich um 08:00 Uhr
  - Zeitzone Europe/Berlin

## Installation

```powershell
cd <Ordner>
python -m pip install -r requirements.txt
```

Dann `config.json` bearbeiten und die gewünschten IP-Adressen eintragen.

Start:

```powershell
python trv_battery_logger.py
```

## Dateien

- `trv_logger.sqlite3` – komplette Messdaten inklusive Rohdaten
- `reports/` – tägliche PDF-Protokolle

## Wichtig

Die Firmware-Erkennung wird aus `/status` und notfalls aus `/debug/log`
abgeleitet. `/stats` wird absichtlich nur bei erkannter 2.2.4 abgefragt.

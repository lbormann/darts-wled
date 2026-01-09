# Connection Diagnostics

## Übersicht

Das `ConnectionDiagnostics` Modul bietet umfassende Verbindungsdiagnose für WLED-Controller und Data-Feeder Verbindungen. Es ist **plattformunabhängig** und funktioniert auf:
- ✅ Windows
- ✅ Linux
- ✅ macOS

## Wann wird die Diagnose ausgeführt?

### 1. **Automatisch im DEBUG-Modus** (`-DEB=1`)

Wenn eine Verbindung verloren geht, wird automatisch eine Diagnose durchgeführt:

```bash
python darts-wled.py -WEPS 192.168.1.20 -DEB=1 [weitere Argumente...]
```

**Auslöser:**
- WebSocket-Error (`on_error_wled`)
- Abnormaler Close (Status Code 1006)
- Verbindungsabbruch ohne Close-Frame

### 2. **Manuell mit Connection Test** (`-CT=1`)

Testet alle konfigurierten Verbindungen einmalig beim Start und beendet die Anwendung:

```bash
python darts-wled.py -WEPS 192.168.1.20 192.168.1.21 -CT=1
```

**Verwendet für:**
- Überprüfung der Netzwerk-Konfiguration
- Troubleshooting vor der ersten Nutzung
- Diagnose bei sporadischen Verbindungsproblemen
- CI/CD Tests

## Diagnose-Schritte

Die Diagnose führt 4 Tests durch:

### Step 1: DNS Resolution
Prüft ob der Hostname aufgelöst werden kann.

**Mögliche Fehler:**
- `DNS_RESOLUTION_FAILED` - Hostname nicht auflösbar

**Lösungen:**
- IP-Adresse direkt verwenden
- DNS-Einstellungen prüfen
- Hostname-Schreibweise überprüfen

### Step 2: TCP Connection
Testet die TCP-Verbindung zum Port.

**Mögliche Fehler:**

| Fehlercode | Kategorie | Beschreibung | Plattform |
|------------|-----------|--------------|-----------|
| 10060 | TIMEOUT | Connection timeout | Windows |
| 10061 | REFUSED | Connection refused | Windows |
| 10013 | PERMISSION | Permission denied | Windows |
| ETIMEDOUT | TIMEOUT | Connection timeout | Unix/Linux/Mac |
| ECONNREFUSED | REFUSED | Connection refused | Unix/Linux/Mac |
| EACCES | PERMISSION | Permission denied | Unix/Linux/Mac |

**Lösungen:**
- **TIMEOUT**: Controller einschalten, IP prüfen, Firewall-Regeln
- **REFUSED**: Service neu starten, Port-Konfiguration prüfen
- **PERMISSION**: Firewall/Antivirus-Einstellungen, als Admin ausführen

### Step 3: HTTP Response
Testet HTTP-Kommunikation mit WLED.

**Mögliche Fehler:**
- `HTTP_TIMEOUT` - Server antwortet nicht
- `HTTP_ERROR` - Ungültiger HTTP-Status

**Lösungen:**
- WLED im Browser öffnen
- LED-Anzahl reduzieren
- Firmware aktualisieren

### Step 4: WebSocket Availability
Prüft ob WebSocket-Endpoint verfügbar ist (nur WLED).

## Beispiel-Ausgabe

### Erfolgreicher Test

```
==============================================================
CONNECTION DIAGNOSTICS: WLED
==============================================================
Host: 192.168.1.20
Port: 80
Platform: Windows
==============================================================

Step 1/4: Testing DNS resolution...
  [OK] DNS resolved: 192.168.1.20 --> 192.168.1.20

Step 2/4: Testing TCP connection...
  [OK] TCP connection successful

Step 3/4: Testing HTTP response...
  [OK] HTTP response successful (Status: 200)
  [OK] Valid WLED response detected

Step 4/4: Testing WebSocket availability...
  [OK] WebSocket endpoint should be available

==============================================================
DIAGNOSTIC SUMMARY
==============================================================
DNS Resolution:    [OK]
  --> Resolved IP: 192.168.1.20
TCP Connection:    [OK]
HTTP Response:     [OK]
WebSocket Ready:   [OK]

Overall Status:    [REACHABLE]
==============================================================
```

### Fehlgeschlagener Test (Timeout)

```
==============================================================
CONNECTION DIAGNOSTICS: WLED
==============================================================
Host: 192.168.1.99
Port: 80
Platform: Windows
==============================================================

Step 1/4: Testing DNS resolution...
  [OK] DNS resolved: 192.168.1.99 --> 192.168.1.99

Step 2/4: Testing TCP connection...
  [ERROR] TCP connection failed: Connection timeout - Host nicht erreichbar oder blockiert
  [ERROR] Error code: 10060 (Category: TIMEOUT)

Step 3/4: Skipped (TCP connection failed)
Step 4/4: Skipped (TCP connection failed)

==============================================================
DIAGNOSTIC SUMMARY
==============================================================
DNS Resolution:    [OK]
  --> Resolved IP: 192.168.1.99
TCP Connection:    [FAILED]
HTTP Response:     [FAILED]
WebSocket Ready:   [FAILED]

Overall Status:    [UNREACHABLE]

Error Type:        TCP_CONNECTION_FAILED
Error Category:    TIMEOUT
Error Code:        10060
Error Details:     Connection timeout - Host nicht erreichbar oder blockiert
==============================================================

==============================================================
TROUBLESHOOTING SUGGESTIONS
==============================================================
Problem: Verbindungs-Timeout

Mögliche Ursachen:
1. WLED-Controller ist ausgeschaltet
2. Falsche IP-Adresse konfiguriert
3. Firewall blockiert die Verbindung
4. Controller ist in anderem Netzwerk/VLAN

Prüfschritte:
- Ping testen: ping 192.168.1.99
- Im Browser öffnen: http://192.168.1.99
- Firewall-Regeln prüfen
- Netzwerk-Verbindung des Controllers prüfen
==============================================================
```

## Verwendung in Produktionsumgebungen

### Als Health-Check im Startup-Script

```bash
#!/bin/bash

# Teste Verbindungen
python darts-wled.py -WEPS 192.168.1.20 192.168.1.21 -CT=1

if [ $? -eq 0 ]; then
    echo "All connections OK - Starting application"
    python darts-wled.py -WEPS 192.168.1.20 192.168.1.21 [weitere Argumente...]
else
    echo "Connection test failed - Check configuration"
    exit 1
fi
```

### PowerShell (Windows)

```powershell
# Teste Verbindungen
python darts-wled.py -WEPS 192.168.1.20 192.168.1.21 -CT=1

if ($LASTEXITCODE -eq 0) {
    Write-Host "All connections OK - Starting application"
    python darts-wled.py -WEPS 192.168.1.20 192.168.1.21 <weitere Argumente...>
} else {
    Write-Host "Connection test failed - Check configuration"
    exit 1
}
```

## Fehlercodes-Referenz

### Windows

| Code | Name | Bedeutung |
|------|------|-----------|
| 10060 | WSAETIMEDOUT | Connection timeout |
| 10061 | WSAECONNREFUSED | Connection refused |
| 10013 | WSAEACCES | Permission denied |
| 10065 | WSAEHOSTUNREACH | No route to host |
| 10051 | WSAENETUNREACH | Network unreachable |
| 10054 | WSAECONNRESET | Connection reset |
| 10053 | WSAECONNABORTED | Connection aborted |

### Unix/Linux/macOS

| Code | Name | Bedeutung |
|------|------|-----------|
| ETIMEDOUT | 60/110 | Connection timeout |
| ECONNREFUSED | 61/111 | Connection refused |
| EACCES | 13 | Permission denied |
| EHOSTUNREACH | 65/113 | No route to host |
| ENETUNREACH | 51/101 | Network unreachable |
| ECONNRESET | 54/104 | Connection reset |
| ECONNABORTED | 53/103 | Connection aborted |

## Häufige Probleme und Lösungen

### Problem: "Connection timeout"

**Windows:**
```powershell
# Ping testen
ping 192.168.1.20

# Firewall-Regel hinzufügen
netsh advfirewall firewall add rule name="WLED" dir=out action=allow protocol=TCP remoteport=80

# Firewall Status
netsh advfirewall show allprofiles
```

**Linux:**
```bash
# Ping testen
ping 192.168.1.20

# Firewall prüfen
sudo ufw status
sudo ufw allow out to 192.168.1.20 port 80

# iptables prüfen
sudo iptables -L -n
```

**macOS:**
```bash
# Ping testen
ping 192.168.1.20

# Firewall prüfen
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

### Problem: "Connection refused"

1. **WLED im Browser öffnen:** `http://192.168.1.20`
2. **WLED neu starten:** Controller neu starten
3. **Port prüfen:** Standard ist Port 80

### Problem: "Permission denied"

**Windows:**
- Als Administrator ausführen
- Antivirus/Firewall Ausnahme hinzufügen

**Linux/macOS:**
- Mit `sudo` ausführen (nur bei Ports < 1024)
- Firewall-Regeln anpassen

## API-Nutzung

### Einzelne Verbindung testen

```python
from darts-wled import ConnectionDiagnostics

# Teste WLED Controller
result = ConnectionDiagnostics.diagnose_connection('192.168.1.20', 80, 'WLED')

if result['reachable']:
    print("Controller is reachable!")
else:
    print(f"Error: {result['error_type']}")
    print(f"Details: {result['error_details']}")
```

### Alle Verbindungen testen

```python
from darts-wled import ConnectionDiagnostics

endpoints = ['192.168.1.20', '192.168.1.21']
data_feeder = '127.0.0.1:8079'

results = ConnectionDiagnostics.test_all_connections(endpoints, data_feeder)

for conn_type, endpoint, result in results:
    status = "OK" if result['reachable'] else "FAILED"
    print(f"{status}: {conn_type} - {endpoint}")
```

## Best Practices

1. **Vor der ersten Inbetriebnahme:** Immer mit `-CT=1` testen
2. **Bei sporadischen Problemen:** Debug-Modus aktivieren (`-DEB=1`)
3. **In Produktionsumgebungen:** Health-Check im Startup-Script
4. **Bei Firewall-Problemen:** Diagnose-Output an Support senden
5. **Dokumentation:** Ausgabe der Diagnose für Troubleshooting speichern

## Support

Bei Problemen bitte folgende Informationen bereitstellen:

1. Betriebssystem und Version
2. Komplette Diagnose-Ausgabe (`-CT=1`)
3. Netzwerk-Topologie (Router, VLANs, etc.)
4. Firewall/Antivirus Software
5. WLED-Version

Diagnose-Ausgabe kann mit Umleitung gespeichert werden:

```bash
# Windows PowerShell
python darts-wled.py -WEPS 192.168.1.20 -CT=1 > diagnostics.log 2>&1

# Linux/macOS
python darts-wled.py -WEPS 192.168.1.20 -CT=1 > diagnostics.log 2>&1
```

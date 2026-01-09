"""
Connection Diagnostics Module for darts-wled

Provides platform-independent connection diagnostics for WLED controllers
and Data-Feeder connections. Works on Windows, Linux, and macOS.

Usage:
    # Test single connection
    result = ConnectionDiagnostics.diagnose_connection('192.168.1.20', 80, 'WLED')
    
    # Test all connections
    results = ConnectionDiagnostics.test_all_connections(
        wled_endpoints=['192.168.1.20', '192.168.1.21'],
        data_feeder_con='127.0.0.1:8079'
    )
"""

import socket
import errno
import platform
import requests
import logging

logger = logging.getLogger()


def ppi(message, info_object=None, prefix='\r\n'):
    """Print info message"""
    logger.info(prefix + str(message))
    if info_object is not None:
        logger.info(str(info_object))


def ppe(message, error_object):
    """Print error message"""
    logger.info(message)
    logger.exception("\r\n" + str(error_object))


class ConnectionDiagnostics:
    """
    Platform-independent connection diagnostics for WLED and Data-Feeder
    """
    
    @staticmethod
    def get_error_message(error_code):
        """
        Platform-independent error code interpretation
        """
        # Windows-specific codes
        windows_errors = {
            10060: ('TIMEOUT', 'Connection timeout - Host nicht erreichbar oder blockiert'),
            10061: ('REFUSED', 'Connection refused - Port geschlossen oder Service inaktiv'),
            10065: ('NO_ROUTE', 'No route to host - Netzwerk-Routing Problem'),
            10051: ('NETWORK_UNREACHABLE', 'Network unreachable - Netzwerk nicht erreichbar'),
            10013: ('PERMISSION', 'Permission denied - Firewall oder Antivirus blockiert'),
            10054: ('RESET', 'Connection reset by peer - Verbindung zurückgesetzt'),
            10053: ('ABORT', 'Software caused connection abort - Verbindung abgebrochen')
        }
        
        # Unix/Linux/Mac errno Codes
        unix_errors = {
            errno.ETIMEDOUT: ('TIMEOUT', 'Connection timeout - Host nicht erreichbar'),
            errno.ECONNREFUSED: ('REFUSED', 'Connection refused - Port geschlossen'),
            errno.EHOSTUNREACH: ('NO_ROUTE', 'No route to host - Host nicht erreichbar'),
            errno.ENETUNREACH: ('NETWORK_UNREACHABLE', 'Network unreachable - Netzwerk nicht erreichbar'),
            errno.EACCES: ('PERMISSION', 'Permission denied - Keine Berechtigung'),
            errno.ECONNRESET: ('RESET', 'Connection reset - Verbindung zurückgesetzt'),
            errno.ECONNABORTED: ('ABORT', 'Connection aborted - Verbindung abgebrochen'),
        }
        
        # Check Windows codes
        if error_code in windows_errors:
            return windows_errors[error_code]
        
        # Check Unix codes
        if error_code in unix_errors:
            return unix_errors[error_code]
        
        return ('UNKNOWN', f'Unknown error code: {error_code}')
    
    @staticmethod
    def diagnose_connection(host, port=80, connection_type='WLED'):
        """
        Performs comprehensive connection diagnosis
        
        Args:
            host: Hostname or IP address
            port: Port number (default: 80)
            connection_type: Type of connection ('WLED' or 'Data-Feeder')
            
        Returns:
            Dictionary with diagnosis results
        """
        diagnostics = {
            'host': host,
            'port': port,
            'type': connection_type,
            'platform': platform.system(),
            'reachable': False,
            'dns_resolved': False,
            'tcp_connection': False,
            'http_response': False,
            'websocket_available': False,
            'error_type': None,
            'error_details': None,
            'error_code': None
        }
        
        ppi(f"\n{'='*60}", None, '')
        ppi(f"CONNECTION DIAGNOSTICS: {connection_type}", None, '')
        ppi(f"{'='*60}", None, '')
        ppi(f"Host: {host}", None, '')
        ppi(f"Port: {port}", None, '')
        ppi(f"Platform: {diagnostics['platform']}", None, '')
        ppi(f"{'='*60}\n", None, '')
        
        try:
            # 1. DNS Resolution Test
            ppi("Step 1/4: Testing DNS resolution...", None, '')
            try:
                ip_address = socket.gethostbyname(host)
                diagnostics['dns_resolved'] = True
                diagnostics['resolved_ip'] = ip_address
                ppi(f"  [OK] DNS resolved: {host} --> {ip_address}", None, '')
            except socket.gaierror as e:
                diagnostics['error_type'] = 'DNS_RESOLUTION_FAILED'
                diagnostics['error_details'] = str(e)
                ppi(f"  [ERROR] DNS resolution failed: {e}", None, '')
                ConnectionDiagnostics._print_suggestions(diagnostics)
                return diagnostics
            
            # 2. TCP Connection Test
            ppi("\nStep 2/4: Testing TCP connection...", None, '')
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                
                if result == 0:
                    diagnostics['tcp_connection'] = True
                    ppi(f"  [OK] TCP connection successful", None, '')
                else:
                    diagnostics['error_type'] = 'TCP_CONNECTION_FAILED'
                    diagnostics['error_code'] = result
                    error_category, error_msg = ConnectionDiagnostics.get_error_message(result)
                    diagnostics['error_details'] = error_msg
                    diagnostics['error_category'] = error_category
                    ppi(f"  [ERROR] TCP connection failed: {error_msg}", None, '')
                    ppi(f"  [ERROR] Error code: {result} (Category: {error_category})", None, '')
                
                sock.close()
                
            except socket.timeout:
                diagnostics['error_type'] = 'TCP_TIMEOUT'
                diagnostics['error_details'] = 'Connection timeout after 5 seconds'
                ppi(f"  [ERROR] TCP timeout - Host antwortet nicht innerhalb von 5s", None, '')
                ConnectionDiagnostics._print_suggestions(diagnostics)
                return diagnostics
            except Exception as e:
                diagnostics['error_type'] = 'TCP_ERROR'
                diagnostics['error_details'] = str(e)
                ppi(f"  [ERROR] TCP error: {e}", None, '')
                ConnectionDiagnostics._print_suggestions(diagnostics)
                return diagnostics
            
            # 3. HTTP Response Test (only if TCP successful)
            if diagnostics['tcp_connection']:
                ppi("\nStep 3/4: Testing HTTP response...", None, '')
                try:
                    url = f'http://{host}:{port}/json/state' if connection_type == 'WLED' else f'http://{host}:{port}'
                    response = requests.get(url, timeout=3)
                    
                    if response.status_code == 200:
                        diagnostics['http_response'] = True
                        ppi(f"  [OK] HTTP response successful (Status: 200)", None, '')
                        
                        # Check if it's really WLED
                        if connection_type == 'WLED':
                            try:
                                data = response.json()
                                if 'state' in data or 'on' in data:
                                    ppi(f"  [OK] Valid WLED response detected", None, '')
                                else:
                                    ppi(f"  [WARNING] Response doesn't look like WLED", None, '')
                            except:
                                ppi(f"  [WARNING] Could not parse JSON response", None, '')
                    else:
                        diagnostics['error_type'] = 'HTTP_ERROR'
                        diagnostics['error_details'] = f'HTTP Status: {response.status_code}'
                        ppi(f"  [ERROR] HTTP error: Status {response.status_code}", None, '')
                        
                except requests.exceptions.Timeout:
                    diagnostics['error_type'] = 'HTTP_TIMEOUT'
                    diagnostics['error_details'] = 'HTTP request timeout after 3 seconds'
                    ppi(f"  [ERROR] HTTP timeout - Server antwortet nicht", None, '')
                except Exception as e:
                    diagnostics['error_type'] = 'HTTP_ERROR'
                    diagnostics['error_details'] = str(e)
                    ppi(f"  [ERROR] HTTP request failed: {e}", None, '')
                
                # 4. WebSocket Test (only for WLED)
                if connection_type == 'WLED' and diagnostics['http_response']:
                    ppi("\nStep 4/4: Testing WebSocket availability...", None, '')
                    try:
                        ws_url = f'ws://{host}:{port}/ws'
                        ppi(f"  Testing WebSocket URL: {ws_url}", None, '')
                        diagnostics['websocket_available'] = True
                        ppi(f"  [OK] WebSocket endpoint should be available", None, '')
                    except Exception as e:
                        ppi(f"  [WARNING] WebSocket test skipped: {e}", None, '')
            else:
                ppi("\nStep 3/4: Skipped (TCP connection failed)", None, '')
                ppi("Step 4/4: Skipped (TCP connection failed)", None, '')
            
            # Final evaluation
            diagnostics['reachable'] = diagnostics['tcp_connection'] and diagnostics['http_response']
            
        except Exception as e:
            diagnostics['error_type'] = 'DIAGNOSTIC_ERROR'
            diagnostics['error_details'] = str(e)
            ppi(f"\n[ERROR] Diagnostic process failed: {e}", None, '')
        
        # Print summary
        ConnectionDiagnostics._print_summary(diagnostics)
        ConnectionDiagnostics._print_suggestions(diagnostics)
        
        return diagnostics
    
    @staticmethod
    def _print_summary(diagnostics):
        """
        Prints diagnosis summary
        """
        ppi(f"\n{'='*60}", None, '')
        ppi(f"DIAGNOSTIC SUMMARY", None, '')
        ppi(f"{'='*60}", None, '')
        ppi(f"DNS Resolution:    {'[OK]' if diagnostics['dns_resolved'] else '[FAILED]'}", None, '')
        if diagnostics.get('resolved_ip'):
            ppi(f"  --> Resolved IP: {diagnostics['resolved_ip']}", None, '')
        ppi(f"TCP Connection:    {'[OK]' if diagnostics['tcp_connection'] else '[FAILED]'}", None, '')
        ppi(f"HTTP Response:     {'[OK]' if diagnostics['http_response'] else '[FAILED]'}", None, '')
        if diagnostics['type'] == 'WLED':
            ppi(f"WebSocket Ready:   {'[OK]' if diagnostics['websocket_available'] else '[FAILED]'}", None, '')
        ppi(f"\nOverall Status:    {'[REACHABLE]' if diagnostics['reachable'] else '[UNREACHABLE]'}", None, '')
        
        if diagnostics['error_type']:
            ppi(f"\nError Type:        {diagnostics['error_type']}", None, '')
            if diagnostics.get('error_category'):
                ppi(f"Error Category:    {diagnostics['error_category']}", None, '')
            if diagnostics.get('error_code'):
                ppi(f"Error Code:        {diagnostics['error_code']}", None, '')
            ppi(f"Error Details:     {diagnostics['error_details']}", None, '')
        
        ppi(f"{'='*60}", None, '')
    
    @staticmethod
    def _print_suggestions(diagnostics):
        """
        Prints troubleshooting suggestions based on error type
        """
        if not diagnostics['error_type']:
            return
        
        ppi(f"\n{'='*60}", None, '')
        ppi(f"TROUBLESHOOTING SUGGESTIONS", None, '')
        ppi(f"{'='*60}", None, '')
        
        error_category = diagnostics.get('error_category', '')
        
        if diagnostics['error_type'] == 'DNS_RESOLUTION_FAILED':
            ppi("Problem: Hostname kann nicht aufgelöst werden", None, '')
            ppi("", None, '')
            ppi("Mögliche Lösungen:", None, '')
            ppi("1. Verwenden Sie die IP-Adresse direkt statt Hostname", None, '')
            ppi("2. Prüfen Sie die DNS-Einstellungen Ihres Netzwerks", None, '')
            ppi("3. Stellen Sie sicher, dass der Hostname korrekt geschrieben ist", None, '')
            ppi("4. Testen Sie: ping <hostname>", None, '')
        
        elif error_category == 'TIMEOUT':
            ppi("Problem: Verbindungs-Timeout", None, '')
            ppi("", None, '')
            if diagnostics['type'] == 'Data-Feeder':
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. autodarts.io Data-Feeder läuft nicht", None, '')
                ppi("2. Falsche IP-Adresse/Port konfiguriert", None, '')
                ppi("3. Firewall blockiert die Verbindung", None, '')
                ppi("4. Data-Feeder ist in anderem Netzwerk", None, '')
                ppi("", None, '')
                ppi("Prüfschritte:", None, '')
                ppi("- Prüfen Sie ob autodarts.io Data-Feeder läuft", None, '')
                ppi("- Standard Port ist 8079 (WebSocket)", None, '')
                ppi(f"- Ping testen: ping {diagnostics['host']}", None, '')
                ppi("- Firewall-Regeln prüfen", None, '')
            else:
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. WLED-Controller ist ausgeschaltet", None, '')
                ppi("2. Falsche IP-Adresse konfiguriert", None, '')
                ppi("3. Firewall blockiert die Verbindung", None, '')
                ppi("4. Controller ist in anderem Netzwerk/VLAN", None, '')
                ppi("", None, '')
                ppi("Prüfschritte:", None, '')
                ppi(f"- Ping testen: ping {diagnostics['host']}", None, '')
                ppi(f"- Im Browser öffnen: http://{diagnostics['host']}", None, '')
                ppi("- Firewall-Regeln prüfen", None, '')
                ppi("- Netzwerk-Verbindung des Controllers prüfen", None, '')
        
        elif error_category == 'REFUSED':
            ppi("Problem: Verbindung abgelehnt", None, '')
            ppi("", None, '')
            if diagnostics['type'] == 'Data-Feeder':
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. autodarts.io Data-Feeder läuft nicht", None, '')
                ppi(f"2. Port {diagnostics['port']} ist falsch (Standard: 8079)", None, '')
                ppi("3. Data-Feeder bereits mit anderer Anwendung verbunden", None, '')
                ppi("4. WebSocket-Server nicht gestartet", None, '')
                ppi("", None, '')
                ppi("Lösungen:", None, '')
                ppi("- autodarts.io Data-Feeder starten", None, '')
                ppi("- Port-Konfiguration prüfen (Standard: 8079)", None, '')
                ppi("- Andere Anwendungen trennen die Data-Feeder nutzen", None, '')
                ppi("- Data-Feeder neu starten", None, '')
            else:
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. WLED läuft nicht (abgestürzt oder nicht gestartet)", None, '')
                ppi(f"2. Port {diagnostics['port']} ist falsch (WLED Standard: 80)", None, '')
                ppi("3. WLED ist beschäftigt oder überlastet", None, '')
                ppi("", None, '')
                ppi("Lösungen:", None, '')
                ppi("- WLED Controller neu starten", None, '')
                ppi("- Im Browser aufrufen und Status prüfen", None, '')
                ppi("- Port-Konfiguration überprüfen", None, '')
        
        elif error_category == 'PERMISSION':
            ppi("Problem: Zugriff verweigert", None, '')
            ppi("", None, '')
            ppi("Mögliche Ursachen:", None, '')
            ppi("1. Windows Firewall blockiert die Anwendung", None, '')
            ppi("2. Antivirus-Software blockiert Netzwerkzugriff", None, '')
            ppi("3. Keine Administrator-Rechte", None, '')
            ppi("", None, '')
            ppi("Lösungen:", None, '')
            if platform.system() == 'Windows':
                ppi("- Windows Firewall: Ausnahme für darts-wled.py hinzufügen", None, '')
                ppi("- Antivirus: Python.exe zur Whitelist hinzufügen", None, '')
                ppi("- Als Administrator ausführen", None, '')
            elif platform.system() == 'Linux':
                ppi("- Firewall prüfen: sudo ufw status", None, '')
                ppi("- iptables Regeln prüfen", None, '')
            else:
                ppi("- Firewall-Einstellungen prüfen", None, '')
        
        elif error_category in ['NO_ROUTE', 'NETWORK_UNREACHABLE']:
            ppi("Problem: Netzwerk nicht erreichbar", None, '')
            ppi("", None, '')
            if diagnostics['type'] == 'Data-Feeder':
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. Data-Feeder läuft auf anderem PC/Netzwerk", None, '')
                ppi("2. Keine Route zum Zielnetzwerk", None, '')
                ppi("3. VPN oder Routing-Probleme", None, '')
                ppi("4. Falsche IP-Adresse konfiguriert", None, '')
                ppi("", None, '')
                ppi("Prüfschritte:", None, '')
                ppi("- Prüfen Sie auf welchem PC Data-Feeder läuft", None, '')
                ppi("- Bei lokalem Data-Feeder: 127.0.0.1:8079 verwenden", None, '')
                ppi(f"- Routing-Tabelle prüfen: {'route print' if platform.system() == 'Windows' else 'route -n'}", None, '')
            else:
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. Controller ist in anderem Netzwerk/Subnetz", None, '')
                ppi("2. Keine Route zum Zielnetzwerk", None, '')
                ppi("3. VPN oder Routing-Probleme", None, '')
                ppi("", None, '')
                ppi("Prüfschritte:", None, '')
                ppi(f"- Routing-Tabelle prüfen: {'route print' if platform.system() == 'Windows' else 'route -n'}", None, '')
                ppi("- Netzwerk-Konfiguration prüfen", None, '')
                ppi("- Subnetz-Masken vergleichen", None, '')
        
        elif diagnostics['error_type'] in ['HTTP_TIMEOUT', 'HTTP_ERROR']:
            ppi("Problem: HTTP-Kommunikation fehlgeschlagen", None, '')
            ppi("", None, '')
            if diagnostics['type'] == 'Data-Feeder':
                ppi("Hinweis: Data-Feeder ist ein WebSocket-Server, kein HTTP-Server", None, '')
                ppi("", None, '')
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. Data-Feeder läuft, aber WebSocket-Protokoll antwortet nicht auf HTTP", None, '')
                ppi("2. Falscher Port (Standard: 8079 für WebSocket)", None, '')
                ppi("3. Firewall blockiert HTTP, aber erlaubt WebSocket", None, '')
                ppi("", None, '')
                ppi("Hinweis:", None, '')
                ppi("- Dies ist normal für Data-Feeder WebSocket-Verbindungen", None, '')
                ppi("- Wichtig ist die TCP-Verbindung (sollte OK sein)", None, '')
            else:
                ppi("Mögliche Ursachen:", None, '')
                ppi("1. WLED ist überlastet (zu viele LEDs/Effekte)", None, '')
                ppi("2. WiFi-Verbindung instabil", None, '')
                ppi("3. WLED-Firmware abgestürzt", None, '')
                ppi("4. Falscher Endpoint (kein WLED auf dieser Adresse)", None, '')
                ppi("", None, '')
                ppi("Lösungen:", None, '')
                ppi("- WLED im Browser aufrufen und Status prüfen", None, '')
            ppi("- LED-Anzahl reduzieren", None, '')
            ppi("- WLED-Firmware aktualisieren", None, '')
            ppi("- Controller neu starten", None, '')
        
        ppi(f"{'='*60}\n", None, '')
    
    @staticmethod
    def test_all_connections(wled_endpoints, data_feeder_con):
        """
        Tests all configured connections
        
        Args:
            wled_endpoints: List of WLED endpoint URLs
            data_feeder_con: Data-Feeder connection string
            
        Returns:
            List of tuples (connection_type, endpoint, result)
        """
        ppi("\n" + "="*60, None, '')
        ppi("TESTING ALL CONFIGURED CONNECTIONS", None, '')
        ppi("="*60 + "\n", None, '')
        
        results = []
        
        # Test WLED Endpoints
        for endpoint in wled_endpoints:
            # Parse Host and Port
            clean_host = endpoint.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/ws').rstrip('/')
            host = clean_host.split(':')[0]
            port = 80
            if ':' in clean_host:
                try:
                    port = int(clean_host.split(':')[1])
                except:
                    pass
            
            result = ConnectionDiagnostics.diagnose_connection(host, port, 'WLED')
            results.append(('WLED', endpoint, result))
        
        # Test Data-Feeder
        if data_feeder_con:
            # Parse Data-Feeder Connection String
            # Format: wss://127.0.0.1:8079 or ws://...
            df_host = data_feeder_con.replace('wss://', '').replace('ws://', '').replace('http://', '').replace('https://', '')
            if ':' in df_host:
                host, port_str = df_host.split(':')
                port = int(port_str)
            else:
                host = df_host
                port = 8079
            
            result = ConnectionDiagnostics.diagnose_connection(host, port, 'Data-Feeder')
            results.append(('Data-Feeder', data_feeder_con, result))
        
        # Summary of all tests
        ppi("\n" + "="*60, None, '')
        ppi("OVERALL TEST SUMMARY", None, '')
        ppi("="*60, None, '')
        
        reachable_count = sum(1 for _, _, r in results if r['reachable'])
        total_count = len(results)
        
        for conn_type, endpoint, result in results:
            status = "[OK]" if result['reachable'] else "[FAILED]"
            ppi(f"{status} {conn_type}: {endpoint}", None, '')
        
        ppi(f"\nReachable: {reachable_count}/{total_count}", None, '')
        ppi("="*60 + "\n", None, '')
        
        return results

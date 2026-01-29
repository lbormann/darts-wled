import os
import json
import platform
import random
import argparse
import threading
import logging
import sys
from color_constants import colors as WLED_COLORS
from wled_data_manager import WLEDDataManager
from connection_diagnostics import ConnectionDiagnostics
from custom_argument_parser import CustomArgumentParser
import time
import requests
import socketio
import websocket


sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
sh.setFormatter(formatter)
logger=logging.getLogger()
logger.handlers.clear()
logger.setLevel(logging.INFO)
logger.addHandler(sh)



http_session = requests.Session()
http_session.verify = False
# Deaktiviere automatisches Reconnect - wir steuern das manuell
sio = socketio.Client(http_session=http_session, logger=False, engineio_logger=True, reconnection=False)


VERSION = '1.10.2'

DEFAULT_EFFECT_BRIGHTNESS = 175
DEFAULT_EFFECT_IDLE = 'solid|lightgoldenrodyellow'

WLED_EFFECT_LIST_PATH = '/json/eff'
EFFECT_PARAMETER_SEPARATOR = "|"
BOGEY_NUMBERS = [169, 168, 166, 165, 163, 162, 159]
SUPPORTED_CRICKET_FIELDS = [15, 16, 17, 18, 19, 20, 25]
SUPPORTED_GAME_VARIANTS = ['X01', 'Cricket','Tactics', 'Random Checkout', 'ATC', 'RTW', 'CountUp', 'Bermuda', 'Shanghai', 'Gotcha']
WLED_SETTINGS_ARGS={}

# Global WLED Data Manager variable
wled_data_manager = None

# Global flags for connection status
connection_status = {
    'data_feeder': False,
    'wled': False,
    'initialized': False,
    'restart_requested': False,
    'monitoring_started': False,
    'startup_phase': True  # NEU: Flag um Startup-Phase zu tracken
}

# Reconnect tracking per endpoint
reconnect_attempts = {}  # {endpoint_url: {'attempts': 0, 'last_attempt': timestamp, 'backoff': seconds, 'reconnecting': False}}
reconnect_lock = threading.Lock()  # Lock für Thread-sichere Reconnect-Prüfung
MAX_RECONNECT_ATTEMPTS = 10
INITIAL_BACKOFF = 3  # Sekunden
MAX_BACKOFF = 60  # Maximal 60 Sekunden warten
STARTUP_GRACE_PERIOD = 5  # Sekunden: Grace-Period nach Verbindungsaufbau bevor Reconnect aktiv wird

# LED-Count pro Endpoint
led_counts = {}  # {endpoint_url: led_count}

def ppi(message, info_object = None, prefix = '\r\n'):
    logger.info(prefix + str(message))
    if info_object is not None:
        logger.info(str(info_object))
    
def ppe(message, error_object):
    ppi(message)
    if DEBUG:
        logger.exception("\r\n" + str(error_object))


def restart_application():
    """
    Signalisiert einen Neustart ohne den Prozess zu beenden
    """
    ppi("\n" + "="*50, None, '')
    ppi("CONNECTION RESTORED - REINITIALIZING...", None, '')
    ppi("="*50 + "\n", None, '')

    # Close all existing connections
    try:
        if sio.connected:
            sio.disconnect()
    except:
        pass
    
    try:
        global WS_WLEDS
        for ws in WS_WLEDS:
            try:
                if DEBUG:
                    ppi(f"[DEBUG] Closing WebSocket {ws.url}", None, '')
                ws.close()  # Schließt die Verbindung und beendet run_forever()
            except Exception as e:
                if DEBUG:
                    ppi(f"[DEBUG] Error closing {ws.url}: {str(e)}", None, '')
        
        # Kurze Pause damit run_forever() Threads beenden können
        time.sleep(1)
        
        WS_WLEDS = list()  # Liste leeren
        
        if DEBUG:
            ppi(f"[DEBUG] All WebSocket connections closed", None, '')
    except Exception as e:
        if DEBUG:
            ppe("[DEBUG] Error during WebSocket cleanup: ", e)
    
    # Reset Status
    connection_status['data_feeder'] = False
    connection_status['wled'] = False
    connection_status['initialized'] = False
    connection_status['restart_requested'] = True
    connection_status['startup_phase'] = True  # NEU: Reset Startup-Phase für Reconnect
    
    # Reset alle Reconnect-Counter
    global reconnect_attempts
    reconnect_attempts = {}
    if DEBUG:
        ppi("[DEBUG] All reconnect counters reset", None, '')
    
    time.sleep(2)  # Kurze Pause für sauberen Shutdown

def check_data_feeder_connection():
    """
    Prüft ob Data-Feeder erreichbar ist (ohne zu verbinden)
    """
    try:
        server_host = CON.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
        
        # Teste ws:// - mit kürzerem Timeout und reconnection=False
        try:
            test_url = 'ws://' + server_host
            test_sio = socketio.Client(http_session=http_session, logger=False, engineio_logger=False, reconnection=False)
            test_sio.connect(test_url, transports=['websocket'], wait_timeout=2)
            test_sio.disconnect()
            return True
        except:
            pass
        
        # Teste wss://
        try:
            test_url = 'wss://' + server_host
            test_sio = socketio.Client(http_session=http_session, logger=False, engineio_logger=False, reconnection=False)
            test_sio.connect(test_url, transports=['websocket'], wait_timeout=2)
            test_sio.disconnect()
            return True
        except:
            pass
    except:
        pass
    
    return False

def check_wled_connection():
    """
    Prüft ob mindestens ein WLED-Endpoint erreichbar ist
    """
    # for endpoint in WLED_ENDPOINTS:
    #     try:
    #         clean_host = endpoint.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/ws').rstrip('/')
    #         test_url = f'http://{clean_host}/json/state'
    #         response = requests.get(test_url, timeout=6)
    #         if response.status_code == 200:
    #             return True
    #     except:
    #         continue
    # return False
    try:
        clean_host = WLED_ENDPOINT_PRIMARY.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/ws').rstrip('/')
        test_url = f'http://{clean_host}/json/state'
        response = requests.get(test_url, timeout=6)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def wait_for_connections():
    """
    Wartet kontinuierlich bis beide Verbindungen verfügbar sind
    """
    # Wenn wir hier sind während initialized=True, dann ist es ein Restart
    is_restart = connection_status['initialized']
    
    if is_restart:
        ppi("\n" + "="*50, None, '')
        ppi("WAITING FOR RECONNECTION...", None, '')
        ppi("="*50, None, '')
        ppi("Press CTRL+C to exit\n", None, '')
    else:
        ppi("\n" + "="*50)
        ppi("Wait for connections...")
        ppi("="*50)
        ppi("Press CTRL+C to exit\n")

    check_interval = 10  # Sekunden zwischen Prüfungen
    attempt = 0
    
    data_feeder_available = False
    wled_available = False
    
    while True:
        attempt += 1
        current_time = time.strftime("%H:%M:%S")
        
        # Prüfe Data-Feeder
        if not data_feeder_available:
            ppi(f"[{current_time}] Check Data-Feeder ({CON})...", None, '')
            if check_data_feeder_connection():
                ppi(f"[OK] Data-Feeder connected!", None, '')
                data_feeder_available = True
            else:
                ppi(f"[ERROR] Data-Feeder not available", None, '')
        
        # Prüfe WLED
        if not wled_available:
            ppi(f"[{current_time}] Check WLED-Endpoints...", None, '')
            if check_wled_connection():
                ppi(f"[OK] WLED connected!", None, '')
                wled_available = True
            else:
                ppi(f"[ERROR] WLED not available", None, '')
        
        # Wenn beide verfügbar sind
        if data_feeder_available and wled_available:
            ppi("\n" + "="*50, None, '')
            ppi("Both connections available!", None, '')
            ppi("="*50 + "\n", None, '')
            # Fahre mit Initialisierung fort
            return True
        
        # Warte bis zur nächsten Prüfung
        ppi(f"\nNext check in {check_interval} seconds... (Attempt {attempt})\n", None, '')
        time.sleep(check_interval)

def monitor_connections():
    """
    Überwacht kontinuierlich die Verbindungen
    Startet Anwendung neu wenn BEIDE Verbindungen wiederhergestellt sind
    """
    check_interval = 10
    last_check_time = 0
    connection_lost = False
    
    while True:
        time.sleep(1)  # Kurze Sleep-Zyklen für schnellere Reaktion
        
        # Prüfe nur wenn Anwendung bereits initialisiert ist
        if not connection_status['initialized']:
            continue
        
        # Skip wenn bereits ein Restart läuft
        if connection_status['restart_requested']:
            continue
        
        # Prüfe nur alle check_interval Sekunden
        current_timestamp = time.time()
        if current_timestamp - last_check_time < check_interval:
            continue
        
        last_check_time = current_timestamp
        
        data_feeder_status = connection_status['data_feeder']
        wled_status = connection_status['wled']
        
        # Wenn beide Verbindungen aktiv sind
        if data_feeder_status and wled_status:
            if connection_lost:
                # Verbindungen wurden wiederhergestellt!
                ppi("[OK] All connections restored!", None, '')
                connection_lost = False
            continue

        # At least one connection is lost
        if not connection_lost:
            ppi("[WARNING] Connection lost detected", None, '')
            connection_lost = True
        
        # Prüfe ob Verbindungen wiederhergestellt werden können
        current_time = time.strftime("%H:%M:%S")
        
        data_feeder_available = data_feeder_status or check_data_feeder_connection()
        wled_available = wled_status or check_wled_connection()
        
        if not data_feeder_available:
            ppi(f"[{current_time}] [ERROR] Data-Feeder not available", None, '')
        
        if not wled_available:
            ppi(f"[{current_time}] [ERROR] WLED not available", None, '')
        
        # Nur wenn BEIDE wieder verfügbar sind, starte Neuinitialisierung
        if data_feeder_available and wled_available:
            ppi(f"[{current_time}] [OK] Both connections available! Reinitialisation...", None, '')
            restart_application()



# def connect_wled(we):
#     def process(*args):
#         global WS_WLEDS
#         websocket.enableTrace(False)
#         wled_host = we
#         if we.startswith('ws://') == False:
#             wled_host = 'ws://' + we + '/ws'
#         ws = websocket.WebSocketApp(wled_host,
#                                     on_open = on_open_wled,
#                                     on_message = on_message_wled,
#                                     on_error = on_error_wled,
#                                     on_close = on_close_wled)
#         WS_WLEDS.append(ws)

#         ws.run_forever()
#     threading.Thread(target=process).start()

def connect_wled(we):
    def process(*args):
        global WS_WLEDS
        websocket.enableTrace(False)
        
        # Validiere Endpoint - lehne leere/ungültige URLs ab
        if not we or we.strip() == '':
            ppi(f"[ERROR] Invalid WLED endpoint: empty or None", None, '')
            return
        
        # URL-Bereinigung hinzufügen
        wled_host = we.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
        # Entferne auch bereits vorhandenes /ws am Ende
        wled_host = wled_host.rstrip('/ws').rstrip('/')
        
        # Prüfe ob Host nach Bereinigung noch gültig ist
        if not wled_host or wled_host.strip() == '':
            ppi(f"[ERROR] Invalid WLED endpoint after cleanup: {we}", None, '')
            return
        
        wled_host = 'ws://' + wled_host + '/ws'
        
        # NEU: Finde und schließe alte Instanz für diesen Endpoint
        old_ws_list = []
        for ws in WS_WLEDS:
            if ws.url == wled_host:
                old_ws_list.append(ws)
        
        if old_ws_list:
            for old_ws in old_ws_list:
                try:
                    if DEBUG:
                        ppi(f"[DEBUG] Closing old WebSocket instance for {wled_host}", None, '')
                    old_ws.close()  # Schließt WebSocket und beendet run_forever()
                except Exception as e:
                    if DEBUG:
                        ppi(f"[DEBUG] Error closing old WebSocket: {str(e)}", None, '')
            
            # Entferne aus Liste - wichtig: Liste in-place modifizieren!
            WS_WLEDS[:] = [ws for ws in WS_WLEDS if ws.url != wled_host]
            
            if DEBUG:
                ppi(f"[DEBUG] Removed {len(old_ws_list)} old WebSocket instance(s)", None, '')
        
        # Erstelle neue WebSocket-Instanz
        ws = websocket.WebSocketApp(wled_host,
                                    on_open = on_open_wled,
                                    on_message = on_message_wled,
                                    on_error = on_error_wled,
                                    on_close = on_close_wled)
        WS_WLEDS.append(ws)
        
        if DEBUG:
            ppi(f"[DEBUG] Starting new WebSocket thread for {wled_host} (Total WS: {len(WS_WLEDS)})", None, '')
        
        ws.run_forever()
    
    # Thread mit Namen für bessere Identifikation und daemon=True
    thread_name = f"WLED-{we.replace('ws://', '').split('/')[0]}"
    threading.Thread(target=process, name=thread_name, daemon=True).start()

def on_open_wled(ws):
    connection_status['wled'] = True
    ppi(f"[OK] WLED connected: {ws.url}", None, '')
    
    # Reset reconnect counter bei erfolgreicher Verbindung
    if ws.url in reconnect_attempts:
        reconnect_attempts[ws.url] = {'attempts': 0, 'last_attempt': 0, 'backoff': INITIAL_BACKOFF, 'reconnecting': False}
        if DEBUG:
            ppi(f"[DEBUG] Reconnect counter reset for {ws.url}", None, '')
    
    # NEU: Beende Startup-Phase nach Grace-Period
    if connection_status.get('startup_phase', False):
        def end_startup_phase():
            time.sleep(STARTUP_GRACE_PERIOD)
            connection_status['startup_phase'] = False
            if DEBUG:
                ppi(f"[DEBUG] Startup phase ended - Auto-reconnect now active", None, '')
        
        # Starte Timer nur einmal beim ersten erfolgreichen Connect
        threading.Thread(target=end_startup_phase, daemon=True).start()
    
    # Ermittle und cache LED-Anzahl für diesen Endpoint
    led_count = get_led_count(ws.url)
    if led_count > 0 and DEBUG:
        ppi(f"[DEBUG] Cached LED count for {ws.url}: {led_count}", None, '')
    
    if WLED_SOFF is not None and WLED_SOFF == 1:
        control_wled('off', 'WLED Off becouse of Start', bss_requested=False, argument_name='-SOFF')
    else:
        control_wled(IDLE_EFFECT, 'CONNECTED TO WLED ' + str(ws.url), bss_requested=False, argument_name='-IDE')

def on_message_wled(ws, message):
    def process(*args):
        try:
            global lastMessage
            global waitingForIdle
            global waitingForBoardStart
            global idleIndexGlobal
            global playerIndexGlobal

            m = json.loads(message)

            # Erweiterte Fehlerbehandlung mit Endpoint-Info
            if 'error' in m:
                ppe(f"[ERROR] WLED Error from {ws.url}: ", m.get('error'))
                return
            
            if 'success' in m and m['success'] == False:
                ppe(f"[ERROR] WLED Command failed from {ws.url}: ", m.get('message', 'Unknown error'))
                return
            
            # Logging für erfolgreiche State-Updates (nur im Debug-Modus) - kompakte Ausgabe
            if DEBUG and 'state' in m:
                state = m['state']
                # Extrahiere nur die relevanten Werte
                relevant_data = {}
                
                # Preset oder Playlist
                if 'ps' in state and state['ps'] != -1:
                    relevant_data['ps'] = state['ps']
                if 'pl' in state and state['pl'] != -1:
                    relevant_data['pl'] = state['pl']
                
                # On/Off Status
                relevant_data['on'] = state.get('on', False)
                
                # Segment-Daten (nur vom ersten Segment)
                if 'seg' in state and len(state['seg']) > 0:
                    seg = state['seg'][0]
                    seg_data = {}
                    if 'fx' in seg:
                        seg_data['fx'] = seg['fx']
                    if 'col' in seg and len(seg['col']) > 0:
                        seg_data['col'] = seg['col'][0]  # Nur erste Farbe
                    if 'sx' in seg:
                        seg_data['sx'] = seg['sx']
                    if 'ix' in seg:
                        seg_data['ix'] = seg['ix']
                    if 'pal' in seg:
                        seg_data['pal'] = seg['pal']
                    if seg_data:
                        relevant_data['seg'] = seg_data
                
                ppi(f"  [OK] State update from {ws.url}: {json.dumps(relevant_data)}", None, '')
            
            # only process incoming messages of primary wled-endpoint
            if 'info' not in m or m['info']['ip'] != WLED_ENDPOINT_PRIMARY:
                if DEBUG:
                    ppi(f"  [INFO] Ignoring message from non-primary endpoint {ws.url}", None, '')
                return

            if lastMessage != m:
                lastMessage = m
                
                if 'state' in m and waitingForIdle == True: 
                    # Hole den richtigen IDLE-Effekt basierend auf playerIndex
                    idle_effect_list = None
                    if idleIndexGlobal == "0" and IDLE_EFFECT is not None:
                        idle_effect_list = IDLE_EFFECT
                    elif idleIndexGlobal == "1" and IDLE_EFFECT2 is not None:
                        idle_effect_list = IDLE_EFFECT2
                    elif idleIndexGlobal == "2" and IDLE_EFFECT3 is not None:
                        idle_effect_list = IDLE_EFFECT3
                    elif idleIndexGlobal == "3" and IDLE_EFFECT4 is not None:
                        idle_effect_list = IDLE_EFFECT4
                    elif idleIndexGlobal == "4" and IDLE_EFFECT5 is not None:
                        idle_effect_list = IDLE_EFFECT5
                    elif idleIndexGlobal == "5" and IDLE_EFFECT6 is not None:
                        idle_effect_list = IDLE_EFFECT6
                    else:
                        idle_effect_list = IDLE_EFFECT
                    
                    if idle_effect_list is None:
                        return
                    
                    # get_state wählt ein zufälliges Element aus der Liste
                    (ide, duration) = get_state(idle_effect_list)
                    
                    seg = m['state']['seg'][0]

                    is_idle = False
                    if 'ps' in ide and ide['ps'] == str(m['state']['ps']):
                        is_idle = True
                        if DEBUG:
                            ppi(f"  [OK] IDLE detected (Preset {ide['ps']}) from {ws.url}", None, '')
                    elif 'seg' in ide and ide['seg']['fx'] == str(seg['fx']) and m['state']['ps'] == -1 and m['state']['pl'] == -1:
                        is_idle = True
                        if 'col' in ide['seg'] and ide['seg']['col'][0] not in seg['col']:
                            is_idle = False
                        if 'sx' in ide['seg'] and ide['seg']['sx'] != str(seg['sx']):
                            is_idle = False
                        if 'ix' in ide['seg'] and ide['seg']['ix'] != str(seg['ix']):
                            is_idle = False
                        if 'pal' in ide['seg'] and ide['seg']['pal'] != str(seg['pal']):
                            is_idle = False
                        
                        if is_idle and DEBUG:
                            ppi(f"  [OK] IDLE detected (Effect {ide['seg']['fx']}) from {ws.url}", None, '')

                    if is_idle == True:
                        waitingForIdle = False
                        if waitingForBoardStart == True and sio.connected:
                            waitingForBoardStart = False
                            sio.emit('message', 'board-start:' + str(BOARD_STOP_START))
                            if DEBUG:
                                ppi(f"  --> Sent board-start to Data-Feeder", None, '')

        except Exception as e:
            ppe(f'WS-Message processing failed for {ws.url}: ', e)

    threading.Thread(target=process).start()

def on_close_wled(ws, close_status_code, close_msg):
    try:
        connection_status['wled'] = False
        ppi("Websocket [" + str(ws.url) + "] closed! " + str(close_msg) + " - " + str(close_status_code))
        
        # WebSocket Close Status Code Interpretation (nur im DEBUG)
        if DEBUG and close_status_code:
            close_code_messages = {
                1000: 'Normal closure',
                1001: 'Going away - Server shutdown',
                1006: 'Abnormal closure - Keine Close-Frame (Netzwerk/Timeout)',
                1011: 'Internal server error'
            }
            if close_status_code in close_code_messages:
                ppi(f"  Close reason: {close_code_messages[close_status_code]}", None, '')
        
        # NEU: Während Startup-Phase keine automatischen Reconnects
        # Die Startup-Phase endet nach STARTUP_GRACE_PERIOD Sekunden nach dem ersten erfolgreichen Connect
        if connection_status.get('startup_phase', False):
            if DEBUG:
                ppi(f"[DEBUG] Ignoring close during startup phase for {ws.url}", None, '')
            return
        
        # Reconnect-Tracking initialisieren falls nicht vorhanden
        if ws.url not in reconnect_attempts:
            reconnect_attempts[ws.url] = {'attempts': 0, 'last_attempt': 0, 'backoff': INITIAL_BACKOFF, 'reconnecting': False}
        
        # Thread-sichere Prüfung ob bereits ein Reconnect läuft
        with reconnect_lock:
            if reconnect_attempts[ws.url]['reconnecting']:
                if DEBUG:
                    ppi(f"[DEBUG] Reconnect already in progress for {ws.url}, skipping", None, '')
                return
            
            # Markiere als "reconnecting"
            reconnect_attempts[ws.url]['reconnecting'] = True
        
        # Prüfe ob Max-Versuche erreicht
        reconnect_info = reconnect_attempts[ws.url]
        if reconnect_info['attempts'] >= MAX_RECONNECT_ATTEMPTS:
            ppi(f"[WARNING] Maximum reconnect attempts ({MAX_RECONNECT_ATTEMPTS}) reached for {ws.url}", None, '')
            ppi(f"[WARNING] Endpoint {ws.url} will not reconnect automatically", None, '')
            ppi(f"[INFO] Reset via application restart or wait for monitoring thread", None, '')
            reconnect_info['reconnecting'] = False  # Reset flag
            return
        
        # Diagnose nur wenn DEBUG=1 UND CONNECTION_TEST=1
        diagnostics_failed = False
        if DEBUG and CONNECTION_TEST == 1 and (close_status_code == 1006 or close_status_code is None):
            ppi("\n[DEBUG] Abnormal closure detected - Running diagnostics...", None, '')
            
            url_parts = ws.url.replace('ws://', '').replace('wss://', '').split('/')
            host = url_parts[0].split(':')[0]
            port = 80
            
            if ':' in url_parts[0]:
                try:
                    port = int(url_parts[0].split(':')[1])
                except:
                    pass
            
            result = ConnectionDiagnostics.diagnose_connection(host, port, 'WLED')
            diagnostics_failed = not result.get('reachable', False)
        
        # Erhöhe Reconnect-Counter und berechne Backoff
        reconnect_info['attempts'] += 1
        current_time = time.time()
        
        # Bei fehlgeschlagener Diagnose oder HTTP 503: Erhöhe Backoff exponentiell
        if diagnostics_failed:
            reconnect_info['backoff'] = min(reconnect_info['backoff'] * 2, MAX_BACKOFF)
            ppi(f"[INFO] Diagnostics failed - increasing backoff to {reconnect_info['backoff']}s", None, '')
        
        wait_time = reconnect_info['backoff']
        
        ppi(f"Reconnect attempt {reconnect_info['attempts']}/{MAX_RECONNECT_ATTEMPTS} in {wait_time}s : {time.ctime()}", None, '')
        time.sleep(wait_time)
        
        reconnect_info['last_attempt'] = current_time
        
        # Extrahiere Host aus URL und entferne /ws
        original_host = ws.url.replace('ws://', '').replace('wss://', '').split('/')[0]
        
        # Validiere Host vor Reconnect
        if not original_host or original_host.strip() == '':
            ppi(f"[ERROR] Cannot reconnect - invalid host extracted from {ws.url}", None, '')
            ppi(f"[INFO] Endpoint stays in list but won't reconnect until application restart", None, '')
            reconnect_info['reconnecting'] = False  # Reset flag
            return
        
        # Reset reconnecting flag bevor connect_wled aufgerufen wird
        reconnect_info['reconnecting'] = False
        
        connect_wled(original_host)
    except Exception as e:
        ppe('WS-Close failed: ', e)
        # Sicherstellen dass reconnecting flag zurückgesetzt wird
        if ws.url in reconnect_attempts:
            reconnect_attempts[ws.url]['reconnecting'] = False
    
def on_error_wled(ws, error):
    ppe('WLED Controller connection lost WS-Error ' + str(ws.url) + ' failed: ', error)
    
    # Diagnose nur wenn DEBUG=1 UND CONNECTION_TEST=1
    if DEBUG and CONNECTION_TEST == 1:
        url_parts = ws.url.replace('ws://', '').replace('wss://', '').split('/')
        host = url_parts[0].split(':')[0]
        port = 80
        
        if ':' in url_parts[0]:
            try:
                port = int(url_parts[0].split(':')[1])
            except:
                pass
        
        ConnectionDiagnostics.diagnose_connection(host, port, 'WLED')

def control_wled(effect_list, ptext, bss_requested = True, is_win = False, playerIndex = None, argument_name = None):
    global waitingForIdle
    global waitingForBoardStart
    global idleIndexGlobal
    global playerIndexGlobal

    # Prüfe ob Data-Feeder verbunden ist, bevor board-Commands gesendet werden
    if is_win == True and BOARD_STOP_AFTER_WIN == 1 and sio.connected: 
        sio.emit('message', 'board-reset')
        ppi('Board reset after win')
        time.sleep(0.15)

    # if bss_requested == True and (BOARD_STOP_START != 0.0 or is_win == True): 
    # changed becouse of aditional -BSW parameter
    if bss_requested == True and BOARD_STOP_START != 0.0 and sio.connected:
        waitingForBoardStart = True
        sio.emit('message', 'board-stop')
        if is_win == 1:
            time.sleep(0.15)

    #Bord Stop after Win
    if BOARD_STOP_AFTER_WIN != 0 and is_win == True and sio.connected:
        waitingForBoardStart = True
        sio.emit('message', 'board-stop')
        if is_win == 1:
            time.sleep(0.15)
    if effect_list == 'off':
        tempstate = '{"on":false}'
        state = json.loads(tempstate)
        broadcast(state)
    else:
        (state, duration) = get_state(effect_list)
        state.update({'on': True})
        broadcast(state)

    # Erweiterte Ausgabe mit Argument-Name und Endpoint-Info
    endpoint_count = len(WS_WLEDS)
    endpoint_list = [ws.url for ws in WS_WLEDS]
    
    if argument_name:
        if endpoint_count > 1:
            ppi(f"{ptext} [{argument_name}] --> {endpoint_count} endpoints: {', '.join(endpoint_list)}", None, '')
            ppi(f"  WLED Command: {str(state)}", None, '')
        else:
            ppi(f"{ptext} [{argument_name}] --> {endpoint_list[0] if endpoint_list else 'No endpoints'}", None, '')
            ppi(f"  WLED Command: {str(state)}", None, '')
    else:
        if endpoint_count > 1:
            ppi(f"{ptext} --> {endpoint_count} endpoints: {', '.join(endpoint_list)}", None, '')
            ppi(f"  WLED Command: {str(state)}", None, '')
        else:
            ppi(ptext + ' - WLED: ' + str(state))

    if bss_requested == True:
        waitingForIdle = True
        
        wait = EFFECT_DURATION
        if duration is not None:
            wait = duration

        if(wait > 0):
            time.sleep(wait)
            if playerIndex != None:
                if playerIndex == playerIndexGlobal:
                    idleIndexGlobal = playerIndex
                    if playerIndex == '0' and IDLE_EFFECT is not None:
                        (state, duration) = get_state(IDLE_EFFECT)
                    elif playerIndex == '1' and IDLE_EFFECT2 is not None:
                        (state, duration) = get_state(IDLE_EFFECT2)
                    elif playerIndex == '2' and IDLE_EFFECT3 is not None:
                        (state, duration) = get_state(IDLE_EFFECT3)
                    elif playerIndex == '3' and IDLE_EFFECT4 is not None:   
                        (state, duration) = get_state(IDLE_EFFECT4)
                    elif playerIndex == '4' and IDLE_EFFECT5 is not None:
                        (state, duration) = get_state(IDLE_EFFECT5)
                    elif playerIndex == '5' and IDLE_EFFECT6 is not None:
                        (state, duration) = get_state(IDLE_EFFECT6)
                    else:
                        (state, duration) = get_state(IDLE_EFFECT)
                else:
                    
                    idleIndexGlobal = playerIndexGlobal
                    if playerIndexGlobal == '0' and IDLE_EFFECT is not None:
                        (state, duration) = get_state(IDLE_EFFECT)
                    elif playerIndexGlobal == '1' and IDLE_EFFECT2 is not None:
                        (state, duration) = get_state(IDLE_EFFECT2)
                    elif playerIndexGlobal == '2' and IDLE_EFFECT3 is not None:
                        (state, duration) = get_state(IDLE_EFFECT3)
                    elif playerIndexGlobal == '3' and IDLE_EFFECT4 is not None:   
                        (state, duration) = get_state(IDLE_EFFECT4)
                    elif playerIndexGlobal == '4' and IDLE_EFFECT5 is not None:
                        (state, duration) = get_state(IDLE_EFFECT5)
                    elif playerIndexGlobal == '5' and IDLE_EFFECT6 is not None:
                        (state, duration) = get_state(IDLE_EFFECT6)
                    else:
                        (state, duration) = get_state(IDLE_EFFECT)
            else:
                (state, duration) = get_state(IDLE_EFFECT)
            state.update({'on': True})
            broadcast(state)

def get_segment_count():
    """
    Ermittelt die Anzahl der aktiven Segmente vom WLED-Controller (Live-Abfrage)
    """
    try:
        # Immer Live-Abfrage vom Controller für aktuelle Segment-Anzahl
        clean_host = WLED_ENDPOINT_PRIMARY.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/ws').rstrip('/')
        state_url = f'http://{clean_host}/json/state'
        response = requests.get(state_url, timeout=2)
        if response.status_code == 200:
            state_data = response.json()
            if 'seg' in state_data and isinstance(state_data['seg'], list):
                segment_count = len(state_data['seg'])
                if DEBUG:
                    ppi(f"  [DEBUG] Current segment count from controller: {segment_count}", None, '')
                return segment_count
    except Exception as e:
        if DEBUG:
            ppe("Error while determining segment count: ", e)
    
    return 1  # Fallback auf 1 Segment

def get_led_count(endpoint_url=None):
    """
    Ermittelt die Anzahl der LEDs vom WLED-Controller
    
    Args:
        endpoint_url: WebSocket-URL des Endpoints (z.B. 'ws://192.168.1.144/ws')
                     Wenn None, wird WLED_ENDPOINT_PRIMARY verwendet
    """
    global led_counts
    
    try:
        # Bestimme den Host
        if endpoint_url:
            clean_host = endpoint_url.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/ws').rstrip('/')
        else:
            clean_host = WLED_ENDPOINT_PRIMARY.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/ws').rstrip('/')
        
        # Prüfe ob bereits im Cache
        cache_key = f'ws://{clean_host}/ws'
        if cache_key in led_counts and led_counts[cache_key] > 0:
            if DEBUG:
                ppi(f"  [DEBUG] LED count from cache for {cache_key}: {led_counts[cache_key]}", None, '')
            return led_counts[cache_key]
        
        # Versuche aus wled_data_manager zu holen (nur wenn kein spezifischer Endpoint)
        if not endpoint_url and wled_data_manager:
            info = wled_data_manager.wled_data.get('info', {})
            leds = info.get('leds', {})
            count = leds.get('count', 0)
            if count > 0:
                if DEBUG:
                    ppi(f"  [DEBUG] LED count from wled_data_manager: {count}", None, '')
                led_counts[cache_key] = count  # Cache speichern
                return count
        
        # Fallback: Direkte HTTP-Abfrage vom Controller
        info_url = f'http://{clean_host}/json/info'
        response = requests.get(info_url, timeout=2)
        if response.status_code == 200:
            info_data = response.json()
            if 'leds' in info_data and 'count' in info_data['leds']:
                count = info_data['leds']['count']
                led_counts[cache_key] = count  # Cache speichern
                if DEBUG:
                    ppi(f"  [DEBUG] LED count from HTTP request for {clean_host}: {count}", None, '')
                return count
    except Exception as e:
        if DEBUG:
            ppe(f"Error while determining LED count for {endpoint_url or WLED_ENDPOINT_PRIMARY}: ", e)
    
    return 0  # Fallback - WLED verwendet dann seine Default-Einstellung

def prepare_data_for_segments(data, endpoint_url=None):
    """
    Bereitet die Daten vor und setzt Segmente auf Default zurück (außer bei Presets)
    
    Args:
        data: Die zu sendenden WLED-Daten
        endpoint_url: WebSocket-URL des Endpoints (z.B. 'ws://192.168.1.144/ws')
    """
    try:
        if DEBUG:
            ppi(f"  [DEBUG] prepare_data_for_segments INPUT: {json.dumps(data)}", None, '')
        
        # Prüfen ob es sich um ein Preset handelt
        if 'ps' in data:
            # Presets werden unverändert verwendet
            if DEBUG:
                ppi(f"  [DEBUG] Preset detected, returning unchanged", None, '')
            return data
        
        # Für Effekte und Farben: Stelle sicher dass seg ein Array ist
        if 'seg' in data:
            seg_data = data['seg']
            
            # Hole die LED-Anzahl und aktuelle Segment-Anzahl vom Controller (spezifisch für diesen Endpoint!)
            led_count = get_led_count(endpoint_url)
            current_segment_count = get_segment_count()
            
            # Wenn LED-Count nicht ermittelt werden kann, keine Modifikation
            if led_count == 0:
                if DEBUG:
                    ppi(f"  [WARNING] LED count is 0 for {endpoint_url or 'primary'}, skipping segment modification", None, '')
                return data
            if isinstance(seg_data, dict):
                new_segment = {
                    'id': 0,
                    'start': 0,
                    'stop': led_count,
                    # Layout-Felder explizit auf Default-Werte setzen
                    'grp': 1,    # Grouping: 1 = keine Gruppierung
                    'spc': 0,    # Spacing: 0 = kein Abstand
                    'of': 0      # Offset: 0 = kein Offset
                }
                
                # Kopiere nur die Effekt-spezifischen Felder (keine Layout-Felder!)
                effect_fields = ['fx', 'sx', 'ix', 'pal', 'col', 'c1', 'c2', 'c3', 'sel', 'rev', 'mi', 'o1', 'o2', 'o3', 'si', 'm12']
                for field in effect_fields:
                    if field in seg_data:
                        new_segment[field] = seg_data[field]
                modified_data = data.copy()
                segments = [new_segment]
                
                # Deaktiviere alle anderen Segmente (ID 1 bis current_segment_count-1)
                if current_segment_count > 1:
                    for seg_id in range(1, current_segment_count):
                        segments.append({
                            'id': seg_id,
                            'stop': 0  # stop=0 deaktiviert das Segment
                        })
                    if DEBUG:
                        ppi(f"  [INFO] Deactivating {current_segment_count - 1} additional segment(s)", None, '')
                
                modified_data['seg'] = segments
                modified_data['mainseg'] = 0
                
                if DEBUG:
                    ppi(f"  [INFO] Created new segment (0-{led_count} LEDs)", None, '')
                    ppi(f"  [DEBUG] prepare_data_for_segments OUTPUT: {json.dumps(modified_data)}", None, '')
                
                return modified_data
            elif isinstance(seg_data, list):
                # Erstelle ein NEUES Segment basierend auf dem ersten Element
                if len(seg_data) > 0 and isinstance(seg_data[0], dict):
                    new_segment = {
                        'id': 0,
                        'start': 0,
                        'stop': led_count,
                        # Layout-Felder explizit auf Default-Werte setzen
                        'grp': 1,    # Grouping: 1 = keine Gruppierung
                        'spc': 0,    # Spacing: 0 = kein Abstand
                        'of': 0      # Offset: 0 = kein Offset
                    }
                    
                    # Kopiere nur die Effekt-spezifischen Felder (keine Layout-Felder!)
                    effect_fields = ['fx', 'sx', 'ix', 'pal', 'col', 'c1', 'c2', 'c3', 'sel', 'rev', 'mi', 'o1', 'o2', 'o3', 'si', 'm12']
                    for field in effect_fields:
                        if field in seg_data[0]:
                            new_segment[field] = seg_data[0][field]
                    
                    # Erstelle neues Daten-Objekt mit nur einem Segment
                    modified_data = data.copy()
                    segments = [new_segment]
                    
                    # Deaktiviere alle anderen Segmente (ID 1 bis current_segment_count-1)
                    if current_segment_count > 1:
                        for seg_id in range(1, current_segment_count):
                            segments.append({
                                'id': seg_id,
                                'stop': 0  # stop=0 deaktiviert das Segment
                            })
                        if DEBUG:
                            ppi(f"  [INFO] Deactivating {current_segment_count - 1} additional segment(s)", None, '')
                    
                    modified_data['seg'] = segments
                    modified_data['mainseg'] = 0
                    
                    if DEBUG:
                        ppi(f"  [INFO] Created new segment (0-{led_count} LEDs)", None, '')
                        ppi(f"  [DEBUG] prepare_data_for_segments OUTPUT: {json.dumps(modified_data)}", None, '')
                    
                    return modified_data
        
        return data
    except Exception as e:
        ppe("Error while preparing segment data: ", e)
        return data

def broadcast(data):
    """
    Sendet Daten an alle WLED-Endpoints mit detailliertem Logging
    """
    global WS_WLEDS
    
    # Sammle nur aktive Verbindungen zum Senden (aber behalte alle in Liste)
    active_endpoints = []
    for ws in WS_WLEDS:
        # Prüfe ob WebSocket noch offen ist
        if hasattr(ws, 'sock') and ws.sock and ws.sock.connected:
            active_endpoints.append(ws)
        elif DEBUG:
            ppi(f"  [INFO] Skipping closed endpoint (will reconnect later): {ws.url}", None, '')
    
    # Log an welche Endpoints gesendet wird
    if len(active_endpoints) > 0:
        endpoint_urls = [ws.url for ws in active_endpoints]
        if DEBUG or len(active_endpoints) > 1:
            ppi(f"  --> Broadcasting to {len(active_endpoints)} endpoint(s): {', '.join(endpoint_urls)}", None, '')
    else:
        ppi(f"  [WARNING] No active endpoints available for broadcast", None, '')
        return

    results = []
    for wled_ep in active_endpoints:
        try:
            # Bereite Daten spezifisch für diesen Endpoint vor (mit seiner LED-Anzahl!)
            prepared_data = prepare_data_for_segments(data, wled_ep.url)
            
            result = threading.Thread(target=broadcast_intern, args=(wled_ep, prepared_data))
            result.start()
            results.append(result)
        except Exception as e:
            ppe(f"  [ERROR] Failed to start thread for {wled_ep.url}: ", e)
            continue
    
    # Optional: Warte auf alle Threads (für besseres Logging)
    if DEBUG:
        for thread in results:
            thread.join(timeout=1)

def broadcast_intern(endpoint, data):
    """
    Sendet Daten an einen WLED-Endpoint und loggt das Ergebnis
    """
    try:
        endpoint.send(json.dumps(data))
        if DEBUG:
            ppi(f"  [OK] Sent to {endpoint.url}: {json.dumps(data)}", None, '')
        return True
    except Exception as e:
        ppe(f"  [ERROR] Failed to send to {endpoint.url}: ", e)
        return False



def get_state(effect_list):
    if effect_list == ["x"] or effect_list == ["X"]:
        # TODO: add more rnd parameter
        return {"seg": {"fx": str(random.choice(WLED_EFFECT_ID_LIST))} } 
    else:
        return random.choice(effect_list)

def refresh_wled_data():
    """
    Aktualisiert die WLED-Daten bei Bedarf
    """
    global wled_data_manager
    global WLED_EFFECTS
    global WLED_EFFECT_ID_LIST
    
    try:
        if wled_data_manager is None:
            ppi("WLED Data Manager is not initialized")
            return False
            
        sync_result = wled_data_manager.sync_and_save()
        
        if sync_result.get("has_changes", False):
            ppi("WLED data has been updated")
            # Update effects list
            WLED_EFFECTS = wled_data_manager.get_available_effects()
            WLED_EFFECT_ID_LIST = wled_data_manager.get_effect_ids()
            if not WLED_EFFECT_ID_LIST:  # Fallback if no IDs are available
                WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1))

            # Check if the segment count has changed
            segment_count = get_segment_count()
            ppi(f"Current segment count: {segment_count}")

            return True
        return False
    except Exception as e:
        ppe("Error while updating WLED data: ", e)
        return False

def parse_effects_argument(effects_argument, custom_duration_possible = True):
    if effects_argument == None or effects_argument == ["x"] or effects_argument == ["X"]:
        return effects_argument

    parsed_list = list()
    for effect in effects_argument:
        try:
            effect_params = effect.split(EFFECT_PARAMETER_SEPARATOR)
            effect_declaration = effect_params[0].strip().lower()
            
            custom_duration = None

            # preset/ playlist
            if effect_declaration == 'ps':
                state = {effect_declaration : effect_params[1] }
                if custom_duration_possible == True and len(effect_params) >= 3 and effect_params[2].isdigit() == True:
                    custom_duration = int(effect_params[2])
                parsed_list.append((state, custom_duration))
                continue
            
            # effect by ID
            elif effect_declaration.isdigit() == True:
                effect_id = effect_declaration

            # effect by name
            else:
                effect_id = str(WLED_EFFECTS.index(effect_declaration))
            
   

            # everying else .. can have different positions

            # p30
            # ie: "61-120" "29|blueviolet|s255|i255|red1|green1"

            seg = {"fx": effect_id}
 
            colours = list()
            for ep in effect_params[1:]:

                param_key = ep[0].strip().lower()
                param_value = ep[1:].strip().lower()

                # s = speed (sx)
                if param_key == 's' and param_value.isdigit() == True:
                    seg["sx"] = param_value

                # i = intensity (ix)
                elif param_key == 'i' and param_value.isdigit() == True:
                    seg["ix"] = param_value

                # p = palette (pal)
                elif param_key == 'p' and param_value.isdigit() == True:
                    seg["pal"] = param_value

                # du (custom duration)
                elif custom_duration_possible == True and param_key == 'd' and param_value.isdigit() == True:
                    custom_duration = int(param_value)

                # colors 1 - 3 (primary, secondary, tertiary)
                else:
                    color = WLED_COLORS[param_key + param_value]
                    color = list(color)
                    color.append(0)
                    colours.append(color)


            if len(colours) > 0:
                seg["col"] = colours

            parsed_list.append(({"seg": seg}, custom_duration))

        except Exception as e:
            ppe(f"Failed to parse event-configuration '{effect}': ", e)
            continue

    return parsed_list   

def parse_score_area_effects_argument(score_area_effects_arguments):
    if score_area_effects_arguments == None:
        return score_area_effects_arguments

    area = score_area_effects_arguments[0].strip().split('-')
    if len(area) == 2 and area[0].isdigit() and area[1].isdigit():
        return ((int(area[0]), int(area[1])), parse_effects_argument(score_area_effects_arguments[1:]))
    else:
        raise Exception(score_area_effects_arguments[0] + ' is not a valid score-area')

def parse_dartscore_effects_argument(parse_dartscore_effects_argument):
    if parse_dartscore_effects_argument == None:
        return parse_dartscore_effects_argument

    dartscore = parse_dartscore_effects_argument[0].strip().split('-')
    if len(dartscore) == 2 and dartscore[0].isdigit() and dartscore[1].isdigit():
        return ((int(dartscore[0]), int(dartscore[1])), parse_effects_argument(parse_dartscore_effects_argument[1:]))
    else:
        raise Exception(parse_dartscore_effects_argument[0] + ' is not a valid score-area')



def process_lobby(msg):
    if msg['action'] == 'player-joined' and PLAYER_JOINED_EFFECTS is not None:
        control_wled(PLAYER_JOINED_EFFECTS, 'Player joined!', argument_name='-PJ')    
    
    elif msg['action'] == 'player-left' and PLAYER_LEFT_EFFECTS is not None:
        control_wled(PLAYER_LEFT_EFFECTS, 'Player left!', argument_name='-PL')

def process_variant_x01(msg):
    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        
        if SCORE_EFFECTS[val] is not None and len(SCORE_EFFECTS[val]) > 0:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val, playerIndex=msg.get('playerIndex'), argument_name=f'-S{val}')
            # ppi(SCORE_EFFECTS[val])
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val, playerIndex=msg.get('playerIndex'), argument_name=f'-A{SAE}')
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    elif msg['event'] == 'dart1-thrown' or msg['event'] == 'dart2-thrown' or msg['event'] == 'dart3-thrown':
        valDart = str(msg['game']['dartValue'])
        if valDart != '0':
            process_dartscore_effect(valDart, playerIndex=msg.get('playerIndex'))

    elif msg['event'] == 'darts-pulled':
                check_player_idle(msg.get('playerIndex'), 'Darts-pulled next: '+ str(msg.get('player', 'Unknown')))
    elif msg['event'] == 'busted' and BUSTED_EFFECTS is not None:
        control_wled(BUSTED_EFFECTS, 'Busted!', playerIndex=msg.get('playerIndex'), argument_name='-B')

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS is not None:
        if HIGH_FINISH_ON is not None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS is not None:
            control_wled(HIGH_FINISH_EFFECTS, 'Game-won - HIGHFINISH', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-HF')
        else:
            control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-G')

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS is not None:
        if HIGH_FINISH_ON is not None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS is not None:
            control_wled(HIGH_FINISH_EFFECTS, 'Match-won - HIGHFINISH', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-HF')
        else:
            control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-M')

    elif msg['event'] == 'match-started':
                check_player_idle(msg.get('playerIndex'), 'match-started')

    elif msg['event'] == 'game-started':
                check_player_idle(msg.get('playerIndex'), 'game-started')

def process_variant_Bermuda(msg):
    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        
        if SCORE_EFFECTS[val] is not None:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val, playerIndex=msg.get('playerIndex'), argument_name=f'-S{val}')
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val, playerIndex=msg.get('playerIndex'), argument_name=f'-A{SAE}')
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    # elif msg['event'] == 'dart1-thrown' or msg['event'] == 'dart2-thrown' or msg['event'] == 'dart3-thrown':
    #     valDart = str(msg['game']['dartValue'])
    #     if valDart != '0':
    #         process_dartscore_effect(valDart)

    elif msg['event'] == 'darts-pulled':
            check_player_idle(msg.get('playerIndex'), 'Darts-pulled next: '+ str(msg.get('player', 'Unknown')))

    elif msg['event'] == 'busted' and BUSTED_EFFECTS is not None:
        control_wled(BUSTED_EFFECTS, 'Busted!', playerIndex=msg.get('playerIndex'), argument_name='-B')

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS is not None:
        control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-G')

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS is not None:
        control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-M')

    elif msg['event'] == 'match-started':
            check_player_idle(msg.get('playerIndex'), 'match-started')

    elif msg['event'] == 'game-started':
            check_player_idle(msg.get('playerIndex'), 'game-started')

def process_variant_Cricket(msg):
    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        
        if SCORE_EFFECTS[val] is not None:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val, playerIndex=msg.get('playerIndex'), argument_name=f'-S{val}')
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val, playerIndex=msg.get('playerIndex'), argument_name=f'-A{SAE}')
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    elif msg['event'] == 'darts-pulled':
            check_player_idle(msg.get('playerIndex'), 'Darts-pulled next: '+ str(msg.get('player', 'Unknown')))

    elif msg['event'] == 'game-won':
        control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-G')

    elif msg['event'] == 'match-won':
        control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-M')

    elif msg['event'] == 'match-started':
            check_player_idle(msg.get('playerIndex'), 'match-started')

    elif msg['event'] == 'game-started':
            check_player_idle(msg.get('playerIndex'), 'game-started')

def process_variant_ATC(msg):
    if msg['event'] == 'darts-pulled':
            check_player_idle(msg.get('playerIndex'), 'Darts-pulled next: '+ str(msg.get('player', 'Unknown')))

    elif msg['event'] == 'game-won':
        control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-G')

    elif msg['event'] == 'match-won':
        control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg.get('playerIndex'), argument_name='-M')

    elif msg['event'] == 'match-started':
            check_player_idle(msg.get('playerIndex'), 'match-started')

    elif msg['event'] == 'game-started':
            check_player_idle(msg.get('playerIndex'), 'game-started')

def process_dartscore_effect(singledartscore, playerIndex=None):
    if (singledartscore == '25' or singledartscore == '50') and DART_SCORE_BULL_EFFECTS is not None:
        control_wled(DART_SCORE_BULL_EFFECTS, 'Darts-thrown: ' + singledartscore, playerIndex=playerIndex, argument_name='-DSBULL')    
    elif singledartscore in SCORE_DARTSCORE_EFFECTS and SCORE_DARTSCORE_EFFECTS[singledartscore] is not None:
        control_wled(SCORE_DARTSCORE_EFFECTS[singledartscore], 'Darts-thrown: ' + singledartscore, playerIndex=playerIndex, argument_name=f'-DS{singledartscore}')

def process_board_status(msg, playerIndex):
    if msg['event'] == 'Board Status':
        if msg['data']['status'] == 'Board Stopped' and BOARD_STOP_EFFECT is not None and (BOARD_STOP_START == 0.0 or BOARD_STOP_START is None):
           control_wled(BOARD_STOP_EFFECT, 'Board-stopped', bss_requested=False, argument_name='-BSE')
        #    control_wled('test', 'Board-stopped', bss_requested=False)
        elif msg['data']['status'] == 'Board Started':
            check_player_idle(playerIndex, 'Board Started')
        elif msg['data']['status'] == 'Manual reset' and IDLE_EFFECT is not None:
            check_player_idle(playerIndex, 'Manual reset')
        elif msg['data']['status'] == 'Takeout Started' and TAKEOUT_EFFECT is not None:
            control_wled(TAKEOUT_EFFECT, 'Takeout Started', bss_requested=False, argument_name='-TOE')
        elif msg['data']['status'] == 'Takeout Finished':
            check_player_idle(playerIndex, 'Takeout Finished')
        elif msg['data']['status'] == 'Calibration Started' and CALIBRATION_EFFECT is not None:
            control_wled(CALIBRATION_EFFECT, 'Calibration Started', bss_requested=False, argument_name='-CE')
        elif msg['data']['status'] == 'Calibration Finished':
            check_player_idle(playerIndex, 'Calibration Finished')

def process_wled_off():
    if WLED_OFF is not None and WLED_OFF == 1:
        control_wled('off', 'WLED Off', bss_requested=False, argument_name='-OFF')

def check_player_idle(playerIndex, message):
    # Fallback auf '0' wenn playerIndex None ist
    if playerIndex is None:
        playerIndex = '0'
    if playerIndex == '0' and IDLE_EFFECT is not None:
        control_wled(IDLE_EFFECT, message, bss_requested=False, argument_name='-IDE')
    elif playerIndex == '1' and IDLE_EFFECT2 is not None:
        control_wled(IDLE_EFFECT2, message, bss_requested=False, argument_name='-IDE2')
    elif playerIndex == '2' and IDLE_EFFECT3 is not None:
        control_wled(IDLE_EFFECT3, message, bss_requested=False, argument_name='-IDE3')
    elif playerIndex == '3' and IDLE_EFFECT4 is not None:   
        control_wled(IDLE_EFFECT4, message, bss_requested=False, argument_name='-IDE4')
    elif playerIndex == '4' and IDLE_EFFECT5 is not None:
        control_wled(IDLE_EFFECT5, message, bss_requested=False, argument_name='-IDE5')
    elif playerIndex == '5' and IDLE_EFFECT6 is not None:
        control_wled(IDLE_EFFECT6, message, bss_requested=False, argument_name='-IDE6')
    else:
        # Fallback auf IDLE_EFFECT wenn kein Player-spezifischer Effekt definiert ist
        if IDLE_EFFECT is not None:
            control_wled(IDLE_EFFECT, message, bss_requested=False, argument_name='-IDE')

@sio.event
def connect():
    connection_status['data_feeder'] = True
    ppi('CONNECTED TO DATA-FEEDER ' + sio.connection_url)
    WLED_info ={
        'status': 'WLED connected',
        'version': VERSION,
        'settings': WLED_SETTINGS_ARGS
    }
    sio.emit('message', WLED_info)
    if WLED_SOFF is not None and WLED_SOFF == 1:
        control_wled('off', 'WLED Off becouse of Start', bss_requested=False, argument_name='-SOFF')

@sio.event
def connect_error(data):
    ppe("CONNECTION TO DATA-FEEDER FAILED! " + sio.connection_url, data)
    
    # Diagnose nur wenn DEBUG=1 UND CONNECTION_TEST=1
    if DEBUG and CONNECTION_TEST == 1:
        # Parse Connection URL
        url = sio.connection_url.replace('wss://', '').replace('ws://', '').replace('http://', '').replace('https://', '')
        if ':' in url:
            host, port_str = url.split(':')
            port = int(port_str)
        else:
            host = url
            port = 8079
        
        ConnectionDiagnostics.diagnose_connection(host, port, 'Data-Feeder')

@sio.event
def message(msg):
    global playerIndexGlobal
    global idleIndexGlobal
    try:
        if 'playerIndex' in msg:
            playerIndexGlobal = msg['playerIndex']
        # ppi(message)
        if('game' in msg and 'mode' in msg['game']):
            mode = msg['game']['mode']
            if mode == 'X01' or mode == 'Random Checkout' or mode == 'ATC' or mode == 'RTW' or mode == 'CountUp' or mode == 'Shanghai'or mode == 'Gotcha':
                process_variant_x01(msg)
            # elif mode == 'Cricket':
            #     process_match_cricket(msg)
            elif mode == 'Bermuda':
                process_variant_Bermuda(msg)
            elif mode == 'Cricket':
                process_variant_Cricket(msg)
            elif mode == 'ATC' or mode == 'RTW':
                process_variant_ATC(msg)
        elif('event' in msg and msg['event'] == 'lobby'):
            process_lobby(msg)
            playerIndexGlobal = None
            idleIndexGlobal = None
        elif('event' in msg and msg['event'] == 'Board Status'):
            current_player = msg.get('playerIndex', playerIndexGlobal)
            process_board_status(msg, current_player)
        elif('event' in msg and msg['event'] == 'match-ended'):
            process_wled_off()
            playerIndexGlobal = None
            idleIndexGlobal = None

    except Exception as e:
        ppe('DATA-FEEDER Message failed: ', e)

@sio.event
def disconnect():
    connection_status['data_feeder'] = False
    ppi('DISCONNECTED FROM DATA-FEEDER', None, '')
    ppi('Monitoring-Thread will check for reconnection...', None, '')
    
    # Diagnose nur wenn DEBUG=1 UND CONNECTION_TEST=1
    if DEBUG and CONNECTION_TEST == 1:
        # Parse Connection URL
        url = sio.connection_url.replace('wss://', '').replace('ws://', '').replace('http://', '').replace('https://', '')
        if ':' in url:
            host, port_str = url.split(':')
            port = int(port_str)
        else:
            host = url
            port = 8079
        
        ConnectionDiagnostics.diagnose_connection(host, port, 'Data-Feeder')


def connect_data_feeder_with_retry():
    """
    Versucht Data-Feeder-Verbindung herzustellen
    Gibt nach begrenzten Versuchen auf
    """
    def try_connection():
        server_host = CON.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
        
        # Versuch 1: ws://
        try:
            server_url = 'ws://' + server_host
            ppi(f'Verbinde zu {server_url}...', None, '')
            sio.connect(server_url, transports=['websocket'], wait_timeout=3)
            # Status wird in @sio.event connect() gesetzt
            return True
        except Exception as e:
            if DEBUG:
                ppi(f'WS-Connection failed: {str(e)}', None, '')
        
        # Versuch 2: wss://
        try:
            server_url = 'wss://' + server_host
            ppi(f'Connecting to {server_url} (encrypted)...', None, '')
            sio.connect(server_url, transports=['websocket'], wait_timeout=3)
            # Status wird in @sio.event connect() gesetzt
            return True
        except Exception as e:
            if DEBUG:
                ppi(f'WSS-Connection failed: {str(e)}', None, '')
        
        return False
    
    # Maximal 3 Versuche mit kurzer Verzögerung
    for attempt in range(1, 4):
        if try_connection():
            ppi("[OK] Data-Feeder successfully connected!", None, '')
            return True
        
        if attempt < 3:
            ppi(f'Attempt {attempt}/3 failed, waiting 2s...', None, '')
            time.sleep(2)

    ppi("[ERROR] Data-Feeder connection failed after 3 attempts", None, '')
    connection_status['data_feeder'] = False
    
    # Diagnose nur wenn DEBUG=1 UND CONNECTION_TEST=1
    if DEBUG and CONNECTION_TEST == 1:
        server_host = CON.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
        if ':' in server_host:
            host, port_str = server_host.split(':')
            port = int(port_str)
        else:
            host = server_host
            port = 8079
        
        ConnectionDiagnostics.diagnose_connection(host, port, 'Data-Feeder')
    
    return False


def initialize_connections():
    """
    Initialisiert alle Verbindungen
    Gibt True zurück wenn erfolgreich, False bei Fehler
    """
    global WS_WLEDS
    
    try:
        # Nur beim Restart auf Verbindungen warten
        # Beim ersten Start überspringen wir den Check
        if connection_status['initialized']:
            wait_for_connections()
        
        # Jetzt versuche die Verbindungen herzustellen
        ppi("\n" + "="*50, None, '')
        ppi("STARTING CONNECTION...", None, '')
        ppi("="*50 + "\n", None, '')
        
        connect_data_feeder_with_retry()
        
        for e in WLED_ENDPOINTS:
            connect_wled(e)
        
        # Markiere als initialisiert
        connection_status['initialized'] = True
        
        # Starte Überwachungs-Thread (nur beim ersten Mal)
        if not connection_status['monitoring_started']:
            monitoring_thread = threading.Thread(target=monitor_connections, daemon=True)
            monitoring_thread.start()
            connection_status['monitoring_started'] = True
            ppi("\n[OK] Connection monitoring active\n", None, '')
        else:
            ppi("\n[OK] Connections restored\n", None, '')

        return True

    except Exception as e:
        ppe("Connect failed: ", e)
        return False







if __name__ == "__main__":
    ap = CustomArgumentParser()
    ap.add_argument("-CON", "--connection", default="127.0.0.1:8079", required=False, help="Connection to data feeder")
    ap.add_argument("-WEPS", "--wled_endpoints", required=True, nargs='+', help="Url(s) to wled instance(s)")
    ap.add_argument("-DU", "--effect_duration", type=int, default=0, required=False, help="Duration of a played effect in seconds. After that WLED returns to idle. 0 means infinity duration.")
    ap.add_argument("-BSS", "--board_stop_start", default=0.0, type=float, required=False, help="If greater than 0.0 stops the board before playing effect")
    ap.add_argument("-BRI", "--effect_brightness", type=int, choices=range(1, 256), default=DEFAULT_EFFECT_BRIGHTNESS, required=False, help="Brightness of current effect")
    ap.add_argument("-HFO", "--high_finish_on", type=int, choices=range(1, 171), default=None, required=False, help="Individual score for highfinish")
    ap.add_argument("-HF", "--high_finish_effects", default=None, required=False, nargs='*', help="WLED effect-definition when high-finish occurs")
    ap.add_argument("-IDE", "--idle_effect", default=[DEFAULT_EFFECT_IDLE], required=False, nargs='*', help="WLED effect-definition when waiting for throw")
    ap.add_argument("-IDE2", "--idle_effect_player2", default=None, required=False, nargs='*', help="WLED effect-definition when waiting for throw of Player2")
    ap.add_argument("-IDE3", "--idle_effect_player3", default=None, required=False, nargs='*', help="WLED effect-definition when waiting for throw of Player3")
    ap.add_argument("-IDE4", "--idle_effect_player4", default=None, required=False, nargs='*', help="WLED effect-definition when waiting for throw of Player4")
    ap.add_argument("-IDE5", "--idle_effect_player5", default=None, required=False, nargs='*', help="WLED effect-definition when waiting for throw of Player5")
    ap.add_argument("-IDE6", "--idle_effect_player6", default=None, required=False, nargs='*', help="WLED effect-definition when waiting for throw of Player6")
    ap.add_argument("-G", "--game_won_effects", default=None, required=False, nargs='*', help="WLED effect-definition when game won occurs")
    ap.add_argument("-M", "--match_won_effects", default=None, required=False, nargs='*', help="WLED effect-definition when match won occurs")
    ap.add_argument("-B", "--busted_effects", default=None, required=False, nargs='*', help="WLED effect-definition when bust occurs")
    ap.add_argument("-PJ", "--player_joined_effects", default=None, required=False, nargs='*', help="WLED effect-definition when player-join occurs")
    ap.add_argument("-PL", "--player_left_effects", default=None, required=False, nargs='*', help="WLED effect-definition when player-left occurs")
    for v in range(0, 181):
        val = str(v)
        ap.add_argument("-S" + val, "--score_" + val + "_effects", default=None, required=False, nargs='*', help="WLED effect-definition for score " + val)
    for a in range(1, 13):
        area = str(a)
        ap.add_argument("-A" + area, "--score_area_" + area + "_effects", default=None, required=False, nargs='*', help="WLED effect-definition for score-area")
    ap.add_argument("-DEB", "--debug", type=int, choices=range(0, 2), default=False, required=False, help="If '1', the application will output additional information")
    ap.add_argument("-CT", "--connection_test", type=int, choices=range(0, 2), default=False, required=False, help="If '1', performs connection diagnostics for all endpoints and exits")
    ap.add_argument("-BSW", "--board_stop_after_win", type=int, choices=range(0, 2), default=False, required=False, help="Let the board stop after winning the match check it to activate the board stop")
    ap.add_argument("-BSE", "--board_stop_effect", default=None, required=False, nargs='*', help="WLED effect-definition when Board is stopped")
    ap.add_argument("-TOE", "--takeout_effect", default=None, required=False, nargs='*', help="WLED effect-definition when Takeout will be performed")
    ap.add_argument("-CE", "--calibration_effect", default=None, required=False, nargs='*', help="WLED effect-definition when Calibration will be performed")
    ap.add_argument("-OFF", "--wled_off", type=int, choices=range(0, 2), default=False, required=False, help="Turns WLED Off after game")
    for ds in range(1, 21):
        dartscore = str(ds)
        ap.add_argument("-DS" + dartscore, "--dart_score_" + dartscore + "_effects", default=None, required=False, nargs='*', help="WLED effect-definition score of single dart")
    ap.add_argument("-DSBULL", "--dart_score_BULL_effects", default=None, required=False, nargs='*', help="WLED effect-definition score of single dart")
    # NEEDS TO BE MIGRATED
    ap.add_argument("-SOFF", "--wled_off_at_start", type=int, choices=range(0, 2), default=False, required=False, help="Turns WLED off when extension is started")
    args = vars(ap.parse_args())

    WLED_SETTINGS_ARGS = {
        'connection': args['connection'],
        'wled_endpoints': args['wled_endpoints'],
        'debug': args['debug'],
        'effect_duration': args['effect_duration'],
        'board_stop_start': args['board_stop_start'],
        'board_stop_after_win': args['board_stop_after_win'],
        'effect_brightness': args['effect_brightness'],
        'high_finish_on': args['high_finish_on'],
        'wled_off': args['wled_off'],
        'wled_off_at_start': args['wled_off_at_start'],
        'board_stop_effect': args['board_stop_effect'],
        'takeout_effect': args['takeout_effect'],
        'calibration_effect': args['calibration_effect'],
        'idle_effect': args['idle_effect'],
        'idle_effect_player2': args['idle_effect_player2'],
        'idle_effect_player3': args['idle_effect_player3'],
        'idle_effect_player4': args['idle_effect_player4'],
        'idle_effect_player5': args['idle_effect_player5'],
        'idle_effect_player6': args['idle_effect_player6'],
        'game_won_effects': args['game_won_effects'],
        'match_won_effects': args['match_won_effects'],
        'busted_effects': args['busted_effects'],
        'player_joined_effects': args['player_joined_effects'],
        'player_left_effects': args['player_left_effects']
    }
    for sS in range(0, 181):
        sval = str(sS)
        WLED_SETTINGS_ARGS["score_" + sval + "_effects"] = args["score_" + sval + "_effects"]
    for sds in range(1, 21):
        sdartscore = str(sds)
        WLED_SETTINGS_ARGS["dart_score_" + sdartscore + "_effects"] = args["dart_score_" + sdartscore + "_effects"]
    for sA in range(1, 13):
        sarea = str(sA)
        WLED_SETTINGS_ARGS["score_area_" + sarea + "_effects"] = args["score_area_" + sarea + "_effects"]

    global WS_WLEDS
    global lastMessage
    global waitingForIdle
    global waitingForBoardStart
    global playerIndexGlobal
    global idleIndexGlobal
    
    WS_WLEDS = list()
    lastMessage = None
    waitingForIdle = False
    waitingForBoardStart = False
    playerIndexGlobal = None
    idleIndexGlobal = None

    # ppi('Started with following arguments:')
    # ppi(json.dumps(args, indent=4))

    osType = platform.system()
    osName = os.name
    osRelease = platform.release()
    ppi('\r\n', None, '')
    ppi('##########################################', None, '')
    ppi('       WELCOME TO DARTS-WLED', None, '')
    ppi('##########################################', None, '')
    ppi('VERSION: ' + VERSION, None, '')
    ppi('RUNNING OS: ' + osType + ' | ' + osName + ' | ' + osRelease, None, '')
    ppi('SUPPORTED GAME-VARIANTS: ' + " ".join(str(x) for x in SUPPORTED_GAME_VARIANTS), None, '')
    ppi('DONATION: bitcoin:bc1q8dcva098rrrq2uqhv38rj5hayzrqywhudvrmxa', None, '')
    ppi('\r\n', None, '')

    DEBUG = args['debug']
    CONNECTION_TEST = args['connection_test']
    CON = args['connection']
    # Filtere leere/ungültige WLED Endpoints heraus
    WLED_ENDPOINTS = [ep for ep in args['wled_endpoints'] if ep and ep.strip() != '']
    
    if not WLED_ENDPOINTS:
        ppi('[ERROR] No valid WLED endpoints configured!', None, '')
        sys.exit(1)
    
    WLED_ENDPOINT_PRIMARY = WLED_ENDPOINTS[0]
    EFFECT_DURATION = args['effect_duration']
    BOARD_STOP_START = args['board_stop_start']
    BOARD_STOP_AFTER_WIN = args['board_stop_after_win']
    EFFECT_BRIGHTNESS = args['effect_brightness']
    HIGH_FINISH_ON = args['high_finish_on']
    WLED_OFF = args['wled_off']
    WLED_SOFF = args['wled_off_at_start']
    
    # Connection Test Mode - Teste alle Verbindungen und beende
    if CONNECTION_TEST == 1:
        ppi('\r\n', None, '')
        ppi('##########################################', None, '')
        ppi('   CONNECTION TEST MODE ACTIVATED', None, '')
        ppi('##########################################', None, '')
        ppi('\r\n', None, '')
        
        # Teste alle Verbindungen
        results = ConnectionDiagnostics.test_all_connections(WLED_ENDPOINTS, CON)
        
        # Ausgabe Testergebnis
        ppi('\r\n', None, '')
        ppi('##########################################', None, '')
        ppi('   CONNECTION TEST COMPLETED', None, '')
        all_ok = all(r[2]['reachable'] for r in results)
        if all_ok:
            ppi('   [OK] All connections reachable', None, '')
        else:
            ppi('   [WARNING] Some connections failed', None, '')
            ppi('   --> Application continues anyway', None, '')
        ppi('##########################################', None, '')
        ppi('\r\n', None, '')
    
    # Initialize WLED Data Manager
    wled_data_manager = WLEDDataManager(WLED_ENDPOINT_PRIMARY, "wled_data.json")
    
    # Load existing data or create new
    ppi("Initializing WLED Data Manager...")
    if not wled_data_manager.load_data_from_file():
        ppi("Creating new WLED data file...")
    
    # Sync WLED data at startup
    ppi("Synchronizing WLED data...")
    sync_result = wled_data_manager.sync_and_save()
    
    if sync_result.get("has_changes", False):
        changes = sync_result.get("changes", {})
        ppi("WLED data updated:")
        if "effects" in changes:
            effects_info = changes["effects"]
            ppi(f"  - Effects: {effects_info['total_new']} (previous: {effects_info['total_old']})")
            if effects_info.get("added"):
                ppi(f"    Added: {', '.join(effects_info['added'])}")
            if effects_info.get("removed"):
                ppi(f"    Removed: {', '.join(effects_info['removed'])}")
        if "presets" in changes:
            presets_info = changes["presets"]
            ppi(f"  - Presets: {presets_info['new_count']} (previous: {presets_info['old_count']})")
        if "palettes" in changes:
            palettes_info = changes["palettes"]
            ppi(f"  - Palettes: {palettes_info['new_count']} (previous: {palettes_info['old_count']})")
    else:
        ppi("WLED data is up to date")
    
    # Display WLED data summary
    summary = wled_data_manager.get_data_summary()
    segment_count = get_segment_count()
    ppi(f"WLED-Controller ({summary['endpoint']}):")
    ppi(f"  - {summary['effects_count']} Effects available")
    ppi(f"  - {summary['presets_count']} Presets available")
    ppi(f"  - {summary['palettes_count']} Palettes available")
    ppi(f"  - {segment_count} active segments detected")

    WLED_EFFECTS = list()
    WLED_EFFECT_ID_LIST = []
    
    try:     
        # Use cached effects from data manager instead of making new request
        WLED_EFFECTS = wled_data_manager.get_available_effects()
        WLED_EFFECT_ID_LIST = wled_data_manager.get_effect_ids()
        if not WLED_EFFECT_ID_LIST:  # Fallback wenn keine IDs vorhanden
            WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1))
        ppi("Use cached WLED effects: " + str(len(WLED_EFFECTS)) + " effects loaded")
    except Exception as e:
        # Fallback to original method if data manager fails
        try:
            effect_list_url = 'http://' + WLED_ENDPOINT_PRIMARY + WLED_EFFECT_LIST_PATH
            WLED_EFFECTS = requests.get(effect_list_url, headers={'Accept': 'application/json'})
            WLED_EFFECTS = [we.lower().split('@', 1)[0] for we in WLED_EFFECTS.json()]  
            WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1)) 
            ppi("Fallback - Effects directly loaded from WLED: " + str(len(WLED_EFFECTS)) + " effects")
        except Exception as e2:
            ppe("Failed on receiving effect-list from WLED-Endpoint", e2)
            WLED_EFFECTS = []
            WLED_EFFECT_ID_LIST = []
    
    BOARD_STOP_EFFECT = parse_effects_argument(args['board_stop_effect'])
    TAKEOUT_EFFECT = parse_effects_argument(args['takeout_effect'])
    CALIBRATION_EFFECT = parse_effects_argument(args['calibration_effect'])
    IDLE_EFFECT = parse_effects_argument(args['idle_effect'])
    IDLE_EFFECT2 = parse_effects_argument(args['idle_effect_player2'])
    IDLE_EFFECT3 = parse_effects_argument(args['idle_effect_player3'])
    IDLE_EFFECT4 = parse_effects_argument(args['idle_effect_player4'])
    IDLE_EFFECT5 = parse_effects_argument(args['idle_effect_player5'])
    IDLE_EFFECT6 = parse_effects_argument(args['idle_effect_player6'])
    GAME_WON_EFFECTS = parse_effects_argument(args['game_won_effects'])
    MATCH_WON_EFFECTS = parse_effects_argument(args['match_won_effects'])
    BUSTED_EFFECTS = parse_effects_argument(args['busted_effects'])
    HIGH_FINISH_EFFECTS = parse_effects_argument(args['high_finish_effects'])
    PLAYER_JOINED_EFFECTS = parse_effects_argument(args['player_joined_effects'])
    PLAYER_LEFT_EFFECTS = parse_effects_argument(args['player_left_effects'])

    SCORE_EFFECTS = dict()
    for v in range(0, 181):
        parsed_score = parse_effects_argument(args["score_" + str(v) + "_effects"])
        SCORE_EFFECTS[str(v)] = parsed_score
        # ppi(parsed_score)
        # ppi(SCORE_EFFECTS[str(v)])
    SCORE_AREA_EFFECTS = dict()
    for a in range(1, 13):
        parsed_score_area = parse_score_area_effects_argument(args["score_area_" + str(a) + "_effects"])
        SCORE_AREA_EFFECTS[a] = parsed_score_area
        # ppi(parsed_score_area)
    SCORE_DARTSCORE_EFFECTS = dict()
    for ds in range(1, 21):
        parsed_dartscore = parse_effects_argument(args["dart_score_" + str(ds) + "_effects"])
        SCORE_DARTSCORE_EFFECTS[str(ds)] = parsed_dartscore
        # ppi(parsed_score_area)
    DART_SCORE_BULL_EFFECTS = parse_effects_argument(args['dart_score_BULL_effects'])
    
    # Hauptschleife mit automatischem Neustart
    while True:
        try:
            # Reset restart flag vor Initialisierung
            connection_status['restart_requested'] = False
            
            # Initialisiere Verbindungen
            success = initialize_connections()
            
            if not success:
                # Initialisierung fehlgeschlagen
                ppi("Initialization failed, waiting 5s...", None, '')
                time.sleep(5)
                continue
            
            # Keep main thread alive
            ppi("="*50, None, '')
            ppi("APPLICATION RUNNING", None, '')
            ppi("Press CTRL+C to exit", None, '')
            ppi("="*50 + "\n", None, '')

            # Wait until restart is requested
            while not connection_status['restart_requested']:
                time.sleep(1)

            # Restart has been requested
            ppi("\nPreparing for reinitialization...", None, '')
            
        except KeyboardInterrupt:
            ppi("\nApplication is shutting down...", None, '')
            sys.exit(0)
        except Exception as e:
            ppe("Unexpected error: ", e)
            time.sleep(5)
    



   

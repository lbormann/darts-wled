import os
import json
import platform
import random
import argparse
import threading
import logging
from color_constants import colors as WLED_COLORS
from wled_data_manager import WLEDDataManager
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
sio = socketio.Client(http_session=http_session, logger=True, engineio_logger=True)


VERSION = '1.8.3'

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



def ppi(message, info_object = None, prefix = '\r\n'):
    logger.info(prefix + str(message))
    if info_object is not None:
        logger.info(str(info_object))
    
def ppe(message, error_object):
    ppi(message)
    if DEBUG:
        logger.exception("\r\n" + str(error_object))



def connect_wled(we):
    def process(*args):
        global WS_WLEDS
        websocket.enableTrace(False)
        wled_host = we
        if we.startswith('ws://') == False:
            wled_host = 'ws://' + we + '/ws'
        ws = websocket.WebSocketApp(wled_host,
                                    on_open = on_open_wled,
                                    on_message = on_message_wled,
                                    on_error = on_error_wled,
                                    on_close = on_close_wled)
        WS_WLEDS.append(ws)

        ws.run_forever()
    threading.Thread(target=process).start()

def on_open_wled(ws):
    if WLED_SOFF is not None and WLED_SOFF == 1:
        control_wled('off', 'WLED Off becouse of Start', bss_requested=False)
    else:
        control_wled(IDLE_EFFECT, 'CONNECTED TO WLED ' + str(ws.url), bss_requested=False)

def on_message_wled(ws, message):
    def process(*args):
        try:
            global lastMessage
            global waitingForIdle
            global waitingForBoardStart
            global idleIndexGlobal
            global playerIndexGlobal

            m = json.loads(message)

            # only process incoming messages of primary wled-endpoint
            if 'info' not in m or m['info']['ip'] != WLED_ENDPOINT_PRIMARY:
                return

            if lastMessage != m:
                lastMessage = m

                # ppi(json.dumps(m, indent = 4, sort_keys = True))

                # if 'state' in m :
                #     ppi('server ps: ' + str(m['state']['ps']))
                #     ppi('server pl: ' + str(m['state']['pl']))
                #     ppi('server fx: ' + str(m['state']['seg'][0]['fx']))
                    
                if 'state' in m and waitingForIdle == True: 

                    # [({'seg': {'fx': '0', 'col': [[250, 250, 210, 0]]}, 'on': True}, DURATION)]
                    
                    if idleIndexGlobal == "0" and IDLE_EFFECT is not None:
                        (ide, duration) = IDLE_EFFECT[0]
                    elif idleIndexGlobal == "1" and IDLE_EFFECT2 is not None:
                        (ide, duration) = IDLE_EFFECT2[0]
                    elif idleIndexGlobal == "2" and IDLE_EFFECT3 is not None:
                        (ide, duration) = IDLE_EFFECT3[0]
                    elif idleIndexGlobal == "3" and IDLE_EFFECT4 is not None:
                        (ide, duration) = IDLE_EFFECT4[0]
                    elif idleIndexGlobal == "4" and IDLE_EFFECT5 is not None:
                        (ide, duration) = IDLE_EFFECT5[0]
                    elif idleIndexGlobal == "5" and IDLE_EFFECT6 is not None:
                        (ide, duration) = IDLE_EFFECT6[0]
                    else:
                        (ide, duration) = IDLE_EFFECT[0]
                    seg = m['state']['seg'][0]

                    is_idle = False
                    if 'ps' in ide and ide['ps'] == str(m['state']['ps']):
                        is_idle = True
                    elif ide['seg']['fx'] == str(seg['fx']) and m['state']['ps'] == -1 and m['state']['pl'] == -1:
                        is_idle = True
                        if 'col' in ide['seg'] and ide['seg']['col'][0] not in seg['col']:
                            is_idle = False
                        if 'sx' in ide['seg'] and ide['seg']['sx'] != str(seg['sx']):
                            is_idle = False
                        if 'ix' in ide['seg'] and ide['seg']['ix'] != str(seg['ix']):
                            is_idle = False
                        if 'pal' in ide['seg'] and ide['seg']['pal'] != str(seg['pal']):
                            is_idle = False

                    if is_idle == True:
                        # ppi('Back to IDLE')
                        waitingForIdle = False
                        if waitingForBoardStart == True:
                            waitingForBoardStart = False
                            sio.emit('message', 'board-start:' + str(BOARD_STOP_START))


        except Exception as e:
            ppe('WS-Message failed: ', e)

    threading.Thread(target=process).start()

def on_close_wled(ws, close_status_code, close_msg):
    try:
        ppi("Websocket [" + str(ws.url) + "] closed! " + str(close_msg) + " - " + str(close_status_code))
        ppi("Retry : %s" % time.ctime())
        time.sleep(3)
        connect_wled(ws.url)
    except Exception as e:
        ppe('WS-Close failed: ', e)
    
def on_error_wled(ws, error):
    ppe('WS-Error ' + str(ws.url) + ' failed: ', error)

def control_wled(effect_list, ptext, bss_requested = True, is_win = False, playerIndex = None):
    global waitingForIdle
    global waitingForBoardStart
    global idleIndexGlobal
    global playerIndexGlobal

    if is_win == True and BOARD_STOP_AFTER_WIN == 1: 
        sio.emit('message', 'board-reset')
        ppi('Board reset after win')
        time.sleep(0.15)

    # if bss_requested == True and (BOARD_STOP_START != 0.0 or is_win == True): 
    # changed becouse of aditional -BSW parameter
    if bss_requested == True and BOARD_STOP_START != 0.0:
        waitingForBoardStart = True
        sio.emit('message', 'board-stop')
        if is_win == 1:
            time.sleep(0.15)

    #Bord Stop after Win
    if BOARD_STOP_AFTER_WIN != 0 and is_win == True:
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
    Ermittelt die Anzahl der aktiven Segmente vom WLED-Controller
    """
    try:
        if wled_data_manager:
            return wled_data_manager.get_segment_count()
        else:
            # Fallback: Direkte Abfrage vom Controller
            state_url = f'http://{WLED_ENDPOINT_PRIMARY}/json/state'
            response = requests.get(state_url, timeout=2)
            if response.status_code == 200:
                state_data = response.json()
                if 'seg' in state_data:
                    return len(state_data['seg'])
    except Exception as e:
        ppe("Fehler beim Ermitteln der Segmentanzahl: ", e)
    
    return 1  # Fallback auf 1 Segment

def prepare_data_for_segments(data):
    """
    Bereitet die Daten für alle Segmente vor, außer bei Presets
    """
    try:
        # Prüfen ob es sich um ein Preset handelt
        if 'ps' in data:
            # Presets werden unverändert verwendet
            return data
        
        # Für Effekte und Farben: auf alle Segmente anwenden
        if 'seg' in data:
            segment_count = get_segment_count()
            if segment_count > 1:
                # Erstelle Daten für alle Segmente
                segments_data = []
                original_seg = data['seg']
                
                for i in range(segment_count):
                    segment_data = original_seg.copy()
                    segment_data['id'] = i  # Segment-ID setzen
                    segments_data.append(segment_data)
                
                # Ersetze einzelnes Segment durch Array aller Segmente
                modified_data = data.copy()
                modified_data['seg'] = segments_data
                return modified_data
        
        return data
    except Exception as e:
        ppe("Fehler beim Vorbereiten der Segmentdaten: ", e)
        return data

def broadcast(data):
    global WS_WLEDS

    # Daten für alle Segmente vorbereiten (außer Presets)
    prepared_data = prepare_data_for_segments(data)

    for wled_ep in WS_WLEDS:
        try:
            # ppi("Broadcasting to " + str(wled_ep))
            threading.Thread(target=broadcast_intern, args=(wled_ep, prepared_data)).start()
        except:  
            continue

def broadcast_intern(endpoint, data):
    try:
        endpoint.send(json.dumps(data))
    except:  
        return



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
            ppi("WLED Data Manager ist nicht initialisiert")
            return False
            
        sync_result = wled_data_manager.sync_and_save()
        
        if sync_result.get("has_changes", False):
            ppi("WLED-Daten wurden aktualisiert")
            # Effekte-Liste aktualisieren
            WLED_EFFECTS = wled_data_manager.get_available_effects()
            WLED_EFFECT_ID_LIST = wled_data_manager.get_effect_ids()
            if not WLED_EFFECT_ID_LIST:  # Fallback wenn keine IDs vorhanden
                WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1))
            
            # Prüfen ob sich die Segmentanzahl geändert hat
            segment_count = get_segment_count()
            ppi(f"Aktuelle Segmentanzahl: {segment_count}")
            
            return True
        return False
    except Exception as e:
        ppe("Fehler beim Aktualisieren der WLED-Daten: ", e)
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
            ppe("Failed to parse event-configuration: ", e)
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
        control_wled(PLAYER_JOINED_EFFECTS, 'Player joined!')    
    
    elif msg['action'] == 'player-left' and PLAYER_LEFT_EFFECTS is not None:
        control_wled(PLAYER_LEFT_EFFECTS, 'Player left!')

def process_variant_x01(msg):
    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        
        if SCORE_EFFECTS[val] is not None:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val, playerIndex=msg['playerIndex'])
            ppi(SCORE_EFFECTS[val])
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val, playerIndex=msg['playerIndex'])
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    elif msg['event'] == 'dart1-thrown' or msg['event'] == 'dart2-thrown' or msg['event'] == 'dart3-thrown':
        valDart = str(msg['game']['dartValue'])
        if valDart != '0':
            process_dartscore_effect(valDart)

    elif msg['event'] == 'darts-pulled':
                check_player_idle(msg['playerIndex'], 'Darts-pulled next: '+ str(msg['player']))
    elif msg['event'] == 'busted' and BUSTED_EFFECTS is not None:
        control_wled(BUSTED_EFFECTS, 'Busted!', playerIndex=msg['playerIndex'])

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS is not None:
        if HIGH_FINISH_ON is not None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS is not None:
            control_wled(HIGH_FINISH_EFFECTS, 'Game-won - HIGHFINISH', is_win=True, playerIndex=msg['playerIndex'])
        else:
            control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS is not None:
        if HIGH_FINISH_ON is not None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS is not None:
            control_wled(HIGH_FINISH_EFFECTS, 'Match-won - HIGHFINISH', is_win=True, playerIndex=msg['playerIndex'])
        else:
            control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-started':
                check_player_idle(msg['playerIndex'], 'match-started')

    elif msg['event'] == 'game-started':
                check_player_idle(msg['playerIndex'], 'game-started')

def process_variant_Bermuda(msg):
    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        
        if SCORE_EFFECTS[val] is not None:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val, playerIndex=msg['playerIndex'])
            ppi(SCORE_EFFECTS[val])
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val, playerIndex=msg['playerIndex'])
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    # elif msg['event'] == 'dart1-thrown' or msg['event'] == 'dart2-thrown' or msg['event'] == 'dart3-thrown':
    #     valDart = str(msg['game']['dartValue'])
    #     if valDart != '0':
    #         process_dartscore_effect(valDart)

    elif msg['event'] == 'darts-pulled':
            check_player_idle(msg['playerIndex'], 'Darts-pulled next: '+ str(msg['player']))

    elif msg['event'] == 'busted' and BUSTED_EFFECTS is not None:
        control_wled(BUSTED_EFFECTS, 'Busted!', playerIndex=msg['playerIndex'])

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS is not None:
        control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS is not None:
        control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-started':
            check_player_idle(msg['playerIndex'], 'match-started')

    elif msg['event'] == 'game-started':
            check_player_idle(msg['playerIndex'], 'game-started')

def process_variant_Cricket(msg):
    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        
        if SCORE_EFFECTS[val] is not None:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val, playerIndex=msg['playerIndex'])
            ppi(SCORE_EFFECTS[val])
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val, playerIndex=msg['playerIndex'])
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    elif msg['event'] == 'darts-pulled':
            check_player_idle(msg['playerIndex'], 'Darts-pulled next: '+ str(msg['player']))

    elif msg['event'] == 'game-won':
        control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-won':
        control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-started':
            check_player_idle(msg['playerIndex'], 'match-started')

    elif msg['event'] == 'game-started':
            check_player_idle(msg['playerIndex'], 'game-started')

def process_variant_ATC(msg):
    if msg['event'] == 'darts-pulled':
            check_player_idle(msg['playerIndex'], 'Darts-pulled next: '+ str(msg['player']))

    elif msg['event'] == 'game-won':
        control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-won':
        control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True, playerIndex=msg['playerIndex'])

    elif msg['event'] == 'match-started':
            check_player_idle(msg['playerIndex'], 'match-started')

    elif msg['event'] == 'game-started':
            check_player_idle(msg['playerIndex'], 'game-started')

def process_dartscore_effect(singledartscore):
    if (singledartscore == '25' or singledartscore == '50') and DART_SCORE_BULL_EFFECTS is not None:
        control_wled(DART_SCORE_BULL_EFFECTS, 'Darts-thrown: ' + singledartscore)    
    elif SCORE_DARTSCORE_EFFECTS[singledartscore] is not None:
        # ppi("Singledartscore: "+ singledartscore)
        control_wled(SCORE_DARTSCORE_EFFECTS[singledartscore], 'Darts-thrown: ' + singledartscore)
        

def process_board_status(msg, playerIndex):
    if msg['event'] == 'Board Status':
        if msg['data']['status'] == 'Board Stopped' and BOARD_STOP_EFFECT is not None and (BOARD_STOP_START == 0.0 or BOARD_STOP_START is None):
           control_wled(BOARD_STOP_EFFECT, 'Board-stopped',bss_requested=False)
        #    control_wled('test', 'Board-stopped', bss_requested=False)
        elif msg['data']['status'] == 'Board Started':
            check_player_idle(playerIndex, 'Board Started')
        elif msg['data']['status'] == 'Manual reset' and IDLE_EFFECT is None:
            check_player_idle(playerIndex, 'Manual reset')
        elif msg['data']['status'] == 'Takeout Started' and TAKEOUT_EFFECT is not None:
            control_wled(TAKEOUT_EFFECT, 'Takeout Started', bss_requested=False)
        # elif msg['data']['status'] == 'Takeout Finished':
        #     control_wled(IDLE_EFFECT, 'Takeout Finished', bss_requested=False)
        elif msg['data']['status'] == 'Calibration Started' and CALIBRATION_EFFECT is not None:
            control_wled(CALIBRATION_EFFECT, 'Calibration Started', bss_requested=False)
        elif msg['data']['status'] == 'Calibration Finished':
            check_player_idle(playerIndex, 'Calibration Finished')

def process_wled_off():
    if WLED_OFF is not None and WLED_OFF == 1:
        control_wled('off', 'WLED Off', bss_requested=False)

def check_player_idle(playerIndex, message):
    if playerIndex == '0' and IDLE_EFFECT is not None:
        control_wled(IDLE_EFFECT, message, bss_requested=False)
    elif playerIndex == '1' and IDLE_EFFECT2 is not None:
        control_wled(IDLE_EFFECT2, message, bss_requested=False)
    elif playerIndex == '2' and IDLE_EFFECT3 is not None:
        control_wled(IDLE_EFFECT3, message, bss_requested=False)
    elif playerIndex == '3' and IDLE_EFFECT4 is not None:   
        control_wled(IDLE_EFFECT4, message, bss_requested=False)
    elif playerIndex == '4' and IDLE_EFFECT5 is not None:
        control_wled(IDLE_EFFECT5, message, bss_requested=False)
    elif playerIndex == '5' and IDLE_EFFECT6 is not None:
        control_wled(IDLE_EFFECT6, message, bss_requested=False)
    else:
        control_wled(IDLE_EFFECT, message, bss_requested=False)

@sio.event
def connect():
    ppi('CONNECTED TO DATA-FEEDER ' + sio.connection_url)
    WLED_info ={
        'status': 'WLED connected',
        'version': VERSION,
        'settings': WLED_SETTINGS_ARGS
    }
    sio.emit('message', WLED_info)
    if WLED_SOFF is not None and WLED_SOFF == 1:
        control_wled('off', 'WLED Off becouse of Start', bss_requested=False)

@sio.event
def connect_error(data):
    if DEBUG:
        ppe("CONNECTION TO DATA-FEEDER FAILED! " + sio.connection_url, data)

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
            process_board_status(msg, playerIndexGlobal)
        elif('event' in msg and msg['event'] == 'match-ended'):
            process_wled_off()
            playerIndexGlobal = None
            idleIndexGlobal = None

    except Exception as e:
        ppe('DATA-FEEDER Message failed: ', e)

@sio.event
def disconnect():
    ppi('DISCONNECTED FROM DATA-FEEDER ' + sio.connection_url)



def connect_data_feeder():
    try:
        server_host = CON.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
        server_url = 'ws://' + server_host
        sio.connect(server_url, transports=['websocket'])
    except Exception:
        try:
            server_url = 'wss://' + server_host
            sio.connect(server_url, transports=['websocket'], retry=True, wait_timeout=3)
        except Exception:
            pass







if __name__ == "__main__":
    ap = argparse.ArgumentParser()
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
    ap.add_argument("-BSW", "--board_stop_after_win", type=int, choices=range(0, 2), default=True, required=False, help="Let the board stop after winning the match check it to activate the board stop")
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
    CON = args['connection']
    WLED_ENDPOINTS = list(args['wled_endpoints'])
    WLED_ENDPOINT_PRIMARY = args['wled_endpoints'][0]
    EFFECT_DURATION = args['effect_duration']
    BOARD_STOP_START = args['board_stop_start']
    BOARD_STOP_AFTER_WIN = args['board_stop_after_win']
    EFFECT_BRIGHTNESS = args['effect_brightness']
    HIGH_FINISH_ON = args['high_finish_on']
    WLED_OFF = args['wled_off']
    WLED_SOFF = args['wled_off_at_start']
    
    # Initialize WLED Data Manager
    wled_data_manager = WLEDDataManager(WLED_ENDPOINT_PRIMARY, "wled_data.json")
    
    # Load existing data or create new
    ppi("Initialisiere WLED Data Manager...")
    if not wled_data_manager.load_data_from_file():
        ppi("Erstelle neue WLED-Datendatei...")
    
    # Sync WLED data at startup
    ppi("Synchronisiere WLED-Daten...")
    sync_result = wled_data_manager.sync_and_save()
    
    if sync_result.get("has_changes", False):
        changes = sync_result.get("changes", {})
        ppi("WLED-Daten aktualisiert:")
        if "effects" in changes:
            effects_info = changes["effects"]
            ppi(f"  - Effekte: {effects_info['total_new']} (vorher: {effects_info['total_old']})")
            if effects_info.get("added"):
                ppi(f"    Hinzugefügt: {', '.join(effects_info['added'])}")
            if effects_info.get("removed"):
                ppi(f"    Entfernt: {', '.join(effects_info['removed'])}")
        if "presets" in changes:
            presets_info = changes["presets"]
            ppi(f"  - Presets: {presets_info['new_count']} (vorher: {presets_info['old_count']})")
        if "palettes" in changes:
            palettes_info = changes["palettes"]
            ppi(f"  - Paletten: {palettes_info['new_count']} (vorher: {palettes_info['old_count']})")
    else:
        ppi("WLED-Daten sind aktuell")
    
    # Display WLED data summary
    summary = wled_data_manager.get_data_summary()
    segment_count = get_segment_count()
    ppi(f"WLED-Controller ({summary['endpoint']}):")
    ppi(f"  - {summary['effects_count']} Effekte verfügbar")
    ppi(f"  - {summary['presets_count']} Presets verfügbar") 
    ppi(f"  - {summary['palettes_count']} Paletten verfügbar")
    ppi(f"  - {segment_count} aktive Segmente erkannt")
    
    WLED_EFFECTS = list()
    WLED_EFFECT_ID_LIST = []
    
    try:     
        # Use cached effects from data manager instead of making new request
        WLED_EFFECTS = wled_data_manager.get_available_effects()
        WLED_EFFECT_ID_LIST = wled_data_manager.get_effect_ids()
        if not WLED_EFFECT_ID_LIST:  # Fallback wenn keine IDs vorhanden
            WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1))
        ppi("Verwende gespeicherte WLED-Effekte: " + str(len(WLED_EFFECTS)) + " Effekte")
    except Exception as e:
        # Fallback to original method if data manager fails
        try:
            effect_list_url = 'http://' + WLED_ENDPOINT_PRIMARY + WLED_EFFECT_LIST_PATH
            WLED_EFFECTS = requests.get(effect_list_url, headers={'Accept': 'application/json'})
            WLED_EFFECTS = [we.lower().split('@', 1)[0] for we in WLED_EFFECTS.json()]  
            WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1)) 
            ppi("Fallback - Effekte direkt von WLED geladen: " + str(len(WLED_EFFECTS)) + " Effekte")
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
    try:            
        connect_data_feeder() 
        for e in WLED_ENDPOINTS:
            connect_wled(e)

    except Exception as e:
        ppe("Connect failed: ", e)


time.sleep(5)
    



   

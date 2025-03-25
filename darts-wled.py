import os
import json
import platform
import random
import argparse
import threading
import logging
from color_constants import colors as WLED_COLORS
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


VERSION = '1.7.1'

DEFAULT_EFFECT_BRIGHTNESS = 175
DEFAULT_EFFECT_IDLE = 'solid|lightgoldenrodyellow'

WLED_EFFECT_LIST_PATH = '/json/eff'
EFFECT_PARAMETER_SEPARATOR = "|"
BOGEY_NUMBERS = [169, 168, 166, 165, 163, 162, 159]
SUPPORTED_CRICKET_FIELDS = [15, 16, 17, 18, 19, 20, 25]
SUPPORTED_GAME_VARIANTS = ['X01', 'Cricket', 'Random Checkout', 'ATC', 'RTW', 'CountUp', 'Bermuda', 'Shanghai', 'Gotcha']



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
    control_wled(IDLE_EFFECT, 'CONNECTED TO WLED ' + str(ws.url), bss_requested=False)

def on_message_wled(ws, message):
    def process(*args):
        try:
            global lastMessage
            global waitingForIdle
            global waitingForBoardStart

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

def control_wled(effect_list, ptext, bss_requested = True, is_win = False):
    global waitingForIdle
    global waitingForBoardStart

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
            (state, duration) = get_state(IDLE_EFFECT)
            state.update({'on': True})
            broadcast(state)

def broadcast(data):
    global WS_WLEDS

    for wled_ep in WS_WLEDS:
        try:
            # ppi("Broadcasting to " + str(wled_ep))
            threading.Thread(target=broadcast_intern, args=(wled_ep, data)).start()
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
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val)
            ppi(SCORE_EFFECTS[val])
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] is not None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val)
                        area_found = True
                        break
            if area_found == False:
                ppi('Darts-thrown: ' + val + ' - NOT configured!')

    elif msg['event'] == 'dart1-thrown' or msg['event'] == 'dart2-thrown' or msg['event'] == 'dart3-thrown':
        valDart = str(msg['game']['dartValue'])
        process_dartscore_effect(valDart)

    elif msg['event'] == 'darts-pulled':
        if EFFECT_DURATION == 0:
            control_wled(IDLE_EFFECT, 'Darts-pulled', bss_requested=False)

    elif msg['event'] == 'busted' and BUSTED_EFFECTS is not None:
        control_wled(BUSTED_EFFECTS, 'Busted!')

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS is not None:
        if HIGH_FINISH_ON is not None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS is not None:
            control_wled(HIGH_FINISH_EFFECTS, 'Game-won - HIGHFINISH', is_win=True)
        else:
            control_wled(GAME_WON_EFFECTS, 'Game-won', is_win=True)

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS is not None:
        if HIGH_FINISH_ON is not None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS is not None:
            control_wled(HIGH_FINISH_EFFECTS, 'Match-won - HIGHFINISH', is_win=True)
        else:
            control_wled(MATCH_WON_EFFECTS, 'Match-won', is_win=True)

    elif msg['event'] == 'match-started':
        if EFFECT_DURATION == 0:
            control_wled(IDLE_EFFECT, 'Match-started', bss_requested=False)

    elif msg['event'] == 'game-started':
        if EFFECT_DURATION == 0:
            control_wled(IDLE_EFFECT, 'Game-started', bss_requested=False)


def process_dartscore_effect(singledartscore):
    if (singledartscore == '25' or singledartscore == '50') and DART_SCORE_BULL_EFFECTS is not None:
        control_wled(DART_SCORE_BULL_EFFECTS, 'Darts-thrown: ' + singledartscore)    
    elif SCORE_DARTSCORE_EFFECTS[singledartscore] is not None:
        # ppi("Singledartscore: "+ singledartscore)
        control_wled(SCORE_DARTSCORE_EFFECTS[singledartscore], 'Darts-thrown: ' + singledartscore)
        

def process_board_status(msg):
    if msg['event'] == 'Board Status':
        if msg['data']['status'] == 'Board Stopped' and BOARD_STOP_EFFECT is not None and (BOARD_STOP_START == 0.0 or BOARD_STOP_START is None):
           control_wled(BOARD_STOP_EFFECT, 'Board-stopped', bss_requested=False)
        #    control_wled('test', 'Board-stopped', bss_requested=False)
        elif msg['data']['status'] == 'Board Started':
            control_wled(IDLE_EFFECT, 'Board started', bss_requested=False)
        elif msg['data']['status'] == 'Manual reset':
            control_wled(IDLE_EFFECT, 'Manual reset', bss_requested=False)
        elif msg['data']['status'] == 'Takeout Started' and TAKEOUT_EFFECT is not None:
            control_wled(TAKEOUT_EFFECT, 'Takeout Started', bss_requested=False)
        elif msg['data']['status'] == 'Takeout Finished':
            control_wled(IDLE_EFFECT, 'Takeout Finished', bss_requested=False)
        elif msg['data']['status'] == 'Calibration Started' and CALIBRATION_EFFECT is not None:
            control_wled(CALIBRATION_EFFECT, 'Calibration Started', bss_requested=False)
        elif msg['data']['status'] == 'Calibration Finished':
            control_wled(IDLE_EFFECT, 'Calibration Finished', bss_requested=False)

def process_wled_off():
    if WLED_OFF is not None and WLED_OFF == 1:
        control_wled('off', 'WLED Off', bss_requested=False)

@sio.event
def connect():
    ppi('CONNECTED TO DATA-FEEDER ' + sio.connection_url)
    WLED_info ={
        'status': 'WLED connected',
        'version': VERSION
    }
    sio.emit('message', WLED_info)

@sio.event
def connect_error(data):
    if DEBUG:
        ppe("CONNECTION TO DATA-FEEDER FAILED! " + sio.connection_url, data)

@sio.event
def message(msg):
    try:
        # ppi(message)
        if('game' in msg and 'mode' in msg['game']):
            mode = msg['game']['mode']
            if mode == 'X01' or mode == 'Cricket' or mode == 'Random Checkout' or mode == 'ATC' or mode == 'RTW' or mode == 'CountUp' or mode == 'Bermuda' or mode == 'Shanghai'or mode == 'Gotcha':
                process_variant_x01(msg)
            # elif mode == 'Cricket':
            #     process_match_cricket(msg)
        elif('event' in msg and msg['event'] == 'lobby'):
            process_lobby(msg)
        elif('event' in msg and msg['event'] == 'Board Status'):
            process_board_status(msg)
        elif('event' in msg and msg['event'] == 'match-ended'):
            process_wled_off()

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
    # NEEDS TO BE MIGRATED
    for ds in range(1, 21):
        dartscore = str(ds)
        ap.add_argument("-DS" + dartscore, "--dart_score_" + dartscore + "_effects", default=None, required=False, nargs='*', help="WLED effect-definition score of single dart")
    ap.add_argument("-DSBULL", "--dart_score_BULL_effects", default=None, required=False, nargs='*', help="WLED effect-definition score of single dart")
    
    args = vars(ap.parse_args())


    global WS_WLEDS
    WS_WLEDS = list()

    global lastMessage
    lastMessage = None

    global waitingForIdle
    waitingForIdle = False

    global waitingForBoardStart
    waitingForBoardStart = False

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
    
    WLED_EFFECTS = list()
    try:     
        effect_list_url = 'http://' + WLED_ENDPOINT_PRIMARY + WLED_EFFECT_LIST_PATH
        WLED_EFFECTS = requests.get(effect_list_url, headers={'Accept': 'application/json'})
        WLED_EFFECTS = [we.lower().split('@', 1)[0] for we in WLED_EFFECTS.json()]  
        WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1)) 
        ppi("Your primary WLED-Endpoint (" + effect_list_url + ") offers " + str(len(WLED_EFFECTS)) + " effects")
    except Exception as e:
        ppe("Failed on receiving effect-list from WLED-Endpoint", e)
    
    BOARD_STOP_EFFECT = parse_effects_argument(args['board_stop_effect'])
    TAKEOUT_EFFECT = parse_effects_argument(args['takeout_effect'])
    CALIBRATION_EFFECT = parse_effects_argument(args['calibration_effect'])
    IDLE_EFFECT = parse_effects_argument(args['idle_effect'])
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
    



   

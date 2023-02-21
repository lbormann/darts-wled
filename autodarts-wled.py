import os
import json
import platform
import random
import argparse
from urllib.parse import urlparse
import requests
import websocket
import threading
import json
import logging
logger=logging.getLogger()
from color_constants import colors as WLED_COLORS
import time
import ast


WLED_EFFECT_LIST_PATH = '/json/eff'
DEFAULT_EFFECT_BRIGHTNESS = 175
DEFAULT_EFFECT_IDLE = 'solid|black'
EFFECT_PARAMETER_SEPARATOR = "|"
BOGEY_NUMBERS = [169, 168, 166, 165, 163, 162, 159]
SUPPORTED_CRICKET_FIELDS = [15, 16, 17, 18, 19, 20, 25]
SUPPORTED_GAME_VARIANTS = ['X01', 'Cricket', 'Random Checkout']

VERSION = '1.4.1'
DEBUG = False


def printv(msg, only_debug = False):
    if only_debug == False or (only_debug == True and DEBUG == True):
        print('\r\n>>> ' + str(msg))

def ppjson(js):
    if DEBUG == True:
        print(json.dumps(js, indent = 4, sort_keys = True))

def parseUrl(str):
    parsedUrl = urlparse(str)
    return parsedUrl.scheme + '://' + parsedUrl.netloc + parsedUrl.path.rstrip("/")
    
def log_and_print(message, obj):
    logger.exception(message + str(obj))
    

def broadcast(data):
    global WS_WLEDS

    for wled_ep in WS_WLEDS:
        try:
            # printv("Broadcasting to " + str(wled_ep))
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
            log_and_print("Failed to parse event-configuration: ", e)
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



def control_wled(effect_list, ptext, bss_requested = True):
    global waitingForIdle
    global WS_DATA_FEEDER
    global win

    if bss_requested == True and BOARD_STOP_START != 0.0:
        if BOARD_STOP_START_ONLY_START == 0 or (BOARD_STOP_START_ONLY_START == 1 and win == True):
            WS_DATA_FEEDER.send('board-stop')

    (state, duration) = get_state(effect_list)
    state.update({'on': True})
    broadcast(state)
    waitingForIdle = True
    printv(ptext + ' - WLED: ' + str(state))

    wait = EFFECT_DURATION
    if duration != None:
        wait = duration

    if(wait > 0):
        time.sleep(wait)
        (state, duration) = get_state(IDLE_EFFECT)
        state.update({'on': True})
        broadcast(state)

def process_variant_x01(msg):
    global win

    if msg['event'] == 'darts-thrown':
        win = False
        val = str(msg['game']['dartValue'])
        if SCORE_EFFECTS[val] != None:
            control_wled(SCORE_EFFECTS[val], 'Darts-thrown: ' + val)
        else:
            area_found = False
            ival = int(val)
            for SAE in SCORE_AREA_EFFECTS:
                if SCORE_AREA_EFFECTS[SAE] != None:
                    ((area_from, area_to), AREA_EFFECTS) = SCORE_AREA_EFFECTS[SAE]
                    
                    if ival >= area_from and ival <= area_to:
                        control_wled(AREA_EFFECTS, 'Darts-thrown: ' + val)
                        area_found = True
                        break
            if area_found == False:
                printv('Darts-thrown: ' + val + ' - NOT configured!')

    elif msg['event'] == 'darts-pulled':
        if EFFECT_DURATION == 0:
            control_wled(IDLE_EFFECT, 'Darts-pulled', bss_requested=False)

    elif msg['event'] == 'busted' and BUSTED_EFFECTS != None:
        win = False
        control_wled(BUSTED_EFFECTS, 'Busted!')

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS != None:
        win = True
        if HIGH_FINISH_ON != None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS != None:
            control_wled(HIGH_FINISH_EFFECTS, 'Game-won - HIGHFINISH')
        else:
            control_wled(GAME_WON_EFFECTS, 'Game-won')

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS != None:
        win = True
        if HIGH_FINISH_ON != None and int(msg['game']['dartsThrownValue']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS != None:
            control_wled(HIGH_FINISH_EFFECTS, 'Match-won - HIGHFINISH')
        else:
            control_wled(MATCH_WON_EFFECTS, 'Match-won')

    elif msg['event'] == 'match-started':
        if EFFECT_DURATION == 0:
            control_wled(IDLE_EFFECT, 'Match-started', bss_requested=False)

    elif msg['event'] == 'game-started':
        if EFFECT_DURATION == 0:
            control_wled(IDLE_EFFECT, 'Game-started', bss_requested=False)


def connect_data_feeder():
    def process(*args):
        global WS_DATA_FEEDER
        websocket.enableTrace(False)
        data_feeder_host = CON
        if CON.startswith('ws://') == False:
            data_feeder_host = 'ws://' + CON
        WS_DATA_FEEDER = websocket.WebSocketApp(data_feeder_host,
                                on_open = on_open,
                                on_message = on_message_data_feeder,
                                on_error = on_error,
                                on_close = on_close_data_feeder)

        WS_DATA_FEEDER.run_forever()
    threading.Thread(target=process).start()

def on_message_data_feeder(ws, message):
    def process(*args):
        try:
            # printv(message, only_debug=True)
            msg = ast.literal_eval(message)

            if('game' in msg):
                mode = msg['game']['mode']
                if mode == 'X01' or mode == 'Cricket' or mode == 'Random Checkout':
                    process_variant_x01(msg)
                # elif mode == 'Cricket':
                #     process_match_cricket(msg)

        except Exception as e:
            log_and_print('WS-Message failed: ', e)

    threading.Thread(target=process).start()

def on_close_data_feeder(ws, close_status_code, close_msg):
    try:
        printv("Websocket [" + ws.url + "] closed")
        printv(str(close_msg))
        printv(str(close_status_code))
        printv ("Retry : %s" % time.ctime())
        time.sleep(3)
        connect_data_feeder()
    except Exception as e:
        log_and_print('WS-Close failed: ', e)
    


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
                                on_error = on_error,
                                on_close = on_close_wled)
        WS_WLEDS.append(ws)

        ws.run_forever()
    threading.Thread(target=process).start()

def on_open_wled(ws):
    control_wled(IDLE_EFFECT, 'APP STARTED!')

def on_message_wled(ws, message):
    def process(*args):
        try:
            global lastMessage
            global waitingForIdle
            global win
            global WS_DATA_FEEDER

            m = json.loads(message)

            if lastMessage != m:
                lastMessage = m
                # js = json.dumps(m, indent = 4, sort_keys = True)
                # print(js)

                if 'state' in m and waitingForIdle == True:
                    # [({'seg': {'fx': '0', 'col': [[250, 250, 210, 0]]}, 'on': True}, DURATION)]
                    (ide, duration) = IDLE_EFFECT[0]
                    seg = m['state']['seg'][0]

                    is_idle = True
                    if 'ps' in ide and ide['ps'] != m['state']['ps']:
                        is_idle = False
                    elif ide['seg']['fx'] == str(seg['fx']):
                        if 'col' in ide['seg'] and ide['seg']['col'][0] not in seg['col']:
                            is_idle = False
                        elif 'sx' in ide['seg'] and ide['seg']['sx'] != str(seg['sx']):
                            is_idle = False
                        elif 'ix' in ide['seg'] and ide['seg']['ix'] != str(seg['ix']):
                            is_idle = False
                        elif 'pal' in ide['seg'] and ide['seg']['pal'] != str(seg['pal']):
                            is_idle = False
                    else: 
                        is_idle = False

                    if is_idle == True:
                        waitingForIdle = False

                        if BOARD_STOP_START != 0.0:
                            if BOARD_STOP_START_ONLY_START == 0 or BOARD_STOP_START_ONLY_START == 1 and win == True:
                                win = False
                                WS_DATA_FEEDER.send('board-start:' + str(BOARD_STOP_START))



        except Exception as e:
            log_and_print('WS-Message failed: ', e)

    threading.Thread(target=process).start()

def on_close_wled(ws, close_status_code, close_msg):
    try:
        printv("Websocket [" + ws.url + "] closed")
        printv(str(close_msg))
        printv(str(close_status_code))
        printv ("Retry : %s" % time.ctime())
        time.sleep(3)
        connect_wled(ws.url)
    except Exception as e:
        log_and_print('WS-Close failed: ', e)
    


def on_open(ws):
    printv('Connected to ' + str(ws.url))

def on_error(ws, error):
    log_and_print('WS-Error ' + ws.url + ' failed: ', error)

        



if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-CON", "--connection", default="127.0.0.1:8079", required=False, help="Connection to data feeder")
    ap.add_argument("-WEPS", "--wled_endpoints", required=True, nargs='+', help="Url(s) to wled instance(s)")
    ap.add_argument("-DU", "--effect_duration", type=int, default=0, required=False, help="Duration of a played effect in seconds. After that WLED returns to idle. 0 means infinity duration.")
    ap.add_argument("-BSS", "--board_stop_start", default=0.0, type=float, required=False, help="If greater than 0.0 stops the board before playing effect")
    ap.add_argument("-BSSOS", "--board_stop_start_only_start", type=int, choices=range(0, 2), default=0, required=False, help="Restart Board only on game start")   
    ap.add_argument("-BRI", "--effect_brightness", type=int, choices=range(1, 256), default=DEFAULT_EFFECT_BRIGHTNESS, required=False, help="Brightness of current effect")
    ap.add_argument("-HFO", "--high_finish_on", type=int, choices=range(1, 171), default=None, required=False, help="Individual score for highfinish")
    ap.add_argument("-HF", "--high_finish_effects", default=None, required=False, nargs='*', help="WLED effect-definition when high-finish occurs")
    ap.add_argument("-IDE", "--idle_effect", default=[DEFAULT_EFFECT_IDLE], required=False, nargs='*', help="WLED effect-definition when waiting for throw")
    ap.add_argument("-G", "--game_won_effects", default=None, required=False, nargs='*', help="WLED effect-definition when game won occurs")
    ap.add_argument("-M", "--match_won_effects", default=None, required=False, nargs='*', help="WLED effect-definition when match won occurs")
    ap.add_argument("-B", "--busted_effects", default=None, required=False, nargs='*', help="WLED effect-definition when bust occurs")
    for v in range(0, 181):
        val = str(v)
        ap.add_argument("-S" + val, "--score_" + val + "_effects", default=None, required=False, nargs='*', help="WLED effect-definition for score " + val)
    for a in range(1, 13):
        area = str(a)
        ap.add_argument("-A" + area, "--score_area_" + area + "_effects", default=None, required=False, nargs='*', help="WLED effect-definition for score-area")
    args = vars(ap.parse_args())

   

    global WS_DATA_FEEDER
    WS_DATA_FEEDER = None

    global WS_WLEDS
    WS_WLEDS = list()

    global lastMessage
    lastMessage = None

    global waitingForIdle
    waitingForIdle = True

    global win 
    win = False

    # printv('Started with following arguments:')
    # printv(json.dumps(args, indent=4))

    osType = platform.system()
    osName = os.name
    osRelease = platform.release()
    print('\r\n')
    print('##########################################')
    print('       WELCOME TO AUTODARTS-WLED')
    print('##########################################')
    print('VERSION: ' + VERSION)
    print('RUNNING OS: ' + osType + ' | ' + osName + ' | ' + osRelease)
    print('SUPPORTED GAME-VARIANTS: ' + " ".join(str(x) for x in SUPPORTED_GAME_VARIANTS) )
    print('\r\n')

    CON = args['connection']
    WLED_ENDPOINTS = list(args['wled_endpoints'])
    EFFECT_DURATION = args['effect_duration']
    BOARD_STOP_START = args['board_stop_start']
    BOARD_STOP_START_ONLY_START = args['board_stop_start_only_start']
    EFFECT_BRIGHTNESS = args['effect_brightness']
    HIGH_FINISH_ON = args['high_finish_on']

    IDLE_EFFECT = None
    WLED_EFFECTS = list()
    try:     
        effect_list_url = parseUrl('http://' + args['wled_endpoints'][0] + WLED_EFFECT_LIST_PATH)
        printv("Receiving WLED-effects from " + str(effect_list_url)) 
        WLED_EFFECTS = requests.get(effect_list_url, headers={'Accept': 'application/json'})
        WLED_EFFECTS = [we.lower().split('@', 1)[0] for we in WLED_EFFECTS.json()]  
        WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1)) 
        printv("Your WLED-Endpoint offers " + str(len(WLED_EFFECTS)) + " effects")
        IDLE_EFFECT = parse_effects_argument(args['idle_effect'])
    except Exception as e:
        log_and_print("Failed on receiving effect-list from WLED-Endpoint", e)

    GAME_WON_EFFECTS = parse_effects_argument(args['game_won_effects'])
    MATCH_WON_EFFECTS = parse_effects_argument(args['match_won_effects'])
    BUSTED_EFFECTS = parse_effects_argument(args['busted_effects'])
    HIGH_FINISH_EFFECTS = parse_effects_argument(args['high_finish_effects'])
    

    SCORE_EFFECTS = dict()
    for v in range(0, 181):
        parsed_score = parse_effects_argument(args["score_" + str(v) + "_effects"])
        SCORE_EFFECTS[str(v)] = parsed_score
        printv(parsed_score, True)
    SCORE_AREA_EFFECTS = dict()
    for a in range(1, 13):
        parsed_score_area = parse_score_area_effects_argument(args["score_area_" + str(a) + "_effects"])
        SCORE_AREA_EFFECTS[a] = parsed_score_area
        printv(parsed_score_area, True)


    try:
        connect_data_feeder()
        for e in WLED_ENDPOINTS:
            connect_wled(e)

    except Exception as e:
        log_and_print("Connect failed: ", e)


    



   

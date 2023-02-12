import os
from os import path
import json
import platform
import random
import argparse
from urllib.parse import urlparse
import requests
import threading
import json
import logging
logger=logging.getLogger()
from color_constants import colors as WLED_COLORS
from flask import Flask, request
app = Flask(__name__)



WLED_STATE_PATH = '/json/state'
WLED_EFFECT_LIST_PATH = '/json/eff'
DEFAULT_EFFECT_BRIGHTNESS = 175
EFFECT_PARAMETER_SEPARATOR = "|"
BOGEY_NUMBERS = [169,168,166,165,163,162,159]
SUPPORTED_CRICKET_FIELDS = [15,16,17,18,19,20,25]
SUPPORTED_GAME_VARIANTS = ['X01', 'Random Checkout'] # 'Cricket'

VERSION = '1.2.2'
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
    printv(message + repr(obj))
    logger.exception(message + str(obj))
    

def broadcast(data):
    for wled_ep in WLED_ENDPOINTS:
        try:
            # printv("Broadcasting to " + str(wled_ep))
            threading.Thread(target=broadcast_intern, args=(wled_ep, data)).start()
        except:  
        # except Exception as e:
            # log_and_print('FAILED BROADCAST: ', e)
            continue

def broadcast_intern(endpoint, data):
    try:
        requests.post(endpoint, json=data, verify=False)    
    except:  
    # except Exception as e:
        # log_and_print('FAILED INTERN BROADCAST: ', e)
        return

def get_random_effect(effect_list):
    if effect_list == ["x"] or effect_list == ["X"]:
        return {"fx": str(random.choice(WLED_EFFECT_ID_LIST)) } 
    else:
        return random.choice(effect_list)


def parse_effects_argument(effects_argument):
    if effects_argument == None or effects_argument == ["x"] or effects_argument == ["X"]:
        return effects_argument

    # effects_argument = 
    #     "solid|blueviolet" 
    #     "solid|blue" 
    #     "solid|aliceblue"

    # return:
    # {"fx": 11, col: [[0,0,255,0]]}

    parsed_list = list()
    for effect in effects_argument:
        try:
            effect_params = effect.split(EFFECT_PARAMETER_SEPARATOR)

            # effect-id (fx)
            effect_declaration = effect_params[0].strip()
            if effect_declaration.isdigit() == False:
                effect_id = str(WLED_EFFECTS.index(effect_declaration))
            else:
                effect_id = effect_declaration

            seg = {"fx": effect_id}
            
            # colors 1 - 3 (primary, secondary, tertiary)
            colours = list()
            if(len(effect_params) == 2):
                effect_color_primary = effect_params[1].strip()
                if effect_color_primary.isdigit() == False:
                    effect_color_primary = WLED_COLORS[effect_color_primary]
                effect_color_primary = list(effect_color_primary)
                effect_color_primary.append(0)
                colours = [effect_color_primary]
                
            elif(len(effect_params) == 3):
                effect_color_secondary = effect_params[2].strip()
                if effect_color_secondary.isdigit() == False:
                    effect_color_secondary = WLED_COLORS[effect_color_secondary]
                effect_color_secondary = list(effect_color_secondary)
                effect_color_secondary.append(0)
                colours.append(effect_color_secondary)

            elif(len(effect_params) == 4):
                effect_color_tertiary = effect_params[3].strip()
                if effect_color_tertiary.isdigit() == False:
                    effect_color_tertiary = WLED_COLORS[effect_color_tertiary]
                effect_color_tertiary = list(effect_color_tertiary)
                effect_color_tertiary.append(0)
                colours.append(effect_color_tertiary)

            if len(colours) > 0:
                seg["col"] = colours

            # TODO

            # speed (sx)
            
            # intensity (ix)

            # palette-id (pal)


            # print(seg)

            parsed_list.append(seg)

        except Exception as e:
            log_and_print("Failed to translate names to numbers: ", e)
            continue

    return parsed_list   

def parse_score_area_effects_argument(score_area_effects_arguments):
    if score_area_effects_arguments == None:
        return score_area_effects_arguments

    area = score_area_effects_arguments[0].split('-')
    if len(area) == 2 and area[0].isdigit() and area[1].isdigit():
        return ((int(area[0]), int(area[1])), parse_effects_argument(score_area_effects_arguments[1:]))
    else:
        raise Exception(score_area_effects_arguments[0] + ' is not a valid score-area')

        
def process_match_x01(msg):

    if msg['event'] == 'darts-thrown':
        val = str(msg['game']['dartValue'])
        if SCORE_EFFECTS[val] != None:
            seg = get_random_effect(SCORE_EFFECTS[val])
            broadcast({"on": True, "seg": seg})
            printv('Darts-thrown: ' + val + ' - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])
        else:
            area_found = False
            for SAE in SCORE_AREA_EFFECTS:
                ((area_from, area_to), parsed_effects) = SCORE_AREA_EFFECTS[SAE]
                ival = int(val)
                if ival >= area_from and ival <= area_to:
                    seg = get_random_effect(parsed_effects)
                    broadcast({"on": True, "seg": seg})
                    printv('Darts-thrown: ' + val + ' - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])
                    area_found = True
                    break
            if area_found == False:
                printv('Darts-thrown: ' + val + ' - NO effect configured!')

    elif msg['event'] == 'darts-pulled':
        broadcast({"on": False})
        printv('Darts-pulled')

    elif msg['event'] == 'busted' and BUSTED_EFFECTS != None:
        seg = get_random_effect(BUSTED_EFFECTS)
        broadcast({"on": True, "seg": seg})
        printv('Busted - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])

    elif msg['event'] == 'game-won' and GAME_WON_EFFECTS != None:
        if HIGH_FINISH_ON != None and int(msg['game']['turnPoints']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS != None:
            seg = get_random_effect(HIGH_FINISH_EFFECTS)
            broadcast({"on": True, "seg": seg})
            printv('Game-won - Highfinish - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])
        else:
            seg = get_random_effect(GAME_WON_EFFECTS)
            broadcast({"on": True, "seg": seg})
            printv('Game-won - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])

    elif msg['event'] == 'match-won' and MATCH_WON_EFFECTS != None:
        if HIGH_FINISH_ON != None and int(msg['game']['turnPoints']) >= HIGH_FINISH_ON and HIGH_FINISH_EFFECTS != None:
            seg = get_random_effect(HIGH_FINISH_EFFECTS)
            broadcast({"on": True, "seg": seg})
            printv('Match-won - Highfinish - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])
        else:
            seg = get_random_effect(MATCH_WON_EFFECTS)
            broadcast({"on": True, "seg": seg})
            printv('Match-won - Playing effect ' + seg['fx'] + ' = ' + WLED_EFFECTS[int(seg['fx'])])

    elif msg['event'] == 'game-started':
        broadcast({"on": False})
        printv('Game-started')

def process_match_cricket(msg):
   print('not implement')





@app.route('/', methods=['POST'])
def dartsThrown():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        msg = request.json
        # print(msg)

        mode = msg['game']['mode']
        if mode == 'X01' or mode == 'Random Checkout':
            process_match_x01(msg)
        # elif mode == 'Cricket':
        #     process_match_cricket(msg)
        else:
            return 'Mode ' + mode + ' not supported (yet)!'

        return 'Throw received - We will power your wleds!'
    else:
        return 'Content-Type not supported!'




if __name__ == "__main__":
    ap = argparse.ArgumentParser()

    ap.add_argument("-I", "--host_ip", default="0.0.0.0", required=False, help="ip to be reachable by data feeder")
    ap.add_argument("-P", "--host_port", default="8081", required=False, help="port to be reachable by data feeder")
    ap.add_argument("-WEPS", "--wled_endpoints", required=True, nargs='+', help="Url(s) to wled instance(s)")
    ap.add_argument("-BRI", "--effect_brightness", type=int, choices=range(1, 256), default=DEFAULT_EFFECT_BRIGHTNESS, required=False, help="Brightness of current effect")
    ap.add_argument("-HFO", "--high_finish_on", type=int, choices=range(1, 171), default=None, required=False, help="TODO")
    ap.add_argument("-HF", "--high_finish_effects", default=None, required=False, nargs='*', help="WLED effect-definition when high-finish occurs")
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




    HOST_PORT = args['host_port']
    if(HOST_PORT == None):
        HOST_PORT = '8081'

    HOST_IP = args['host_ip']
    if(HOST_IP == None):
        HOST_IP = '0.0.0.0'   

    WLED_ENDPOINTS = args['wled_endpoints']
    parsedList = list()
    for e in WLED_ENDPOINTS:
        parsedList.append(parseUrl(e + WLED_STATE_PATH))
    WLED_ENDPOINTS = parsedList

    EFFECT_BRIGHTNESS = args['effect_brightness']

    HIGH_FINISH_ON = args['high_finish_on']

    WLED_EFFECTS = list()
    try:     
        effect_list_url = parseUrl(args['wled_endpoints'][0] + WLED_EFFECT_LIST_PATH)
        printv("Receiving WLED-effects from " + str(effect_list_url)) 
        WLED_EFFECTS = requests.get(effect_list_url, headers={'Accept': 'application/json'})
        WLED_EFFECTS = [we.lower() for we in WLED_EFFECTS.json()]  
        WLED_EFFECT_ID_LIST = list(range(0, len(WLED_EFFECTS) + 1)) 
        printv("Your WLED-Endpoint offers " + str(len(WLED_EFFECTS)) + " effects")

        # Turn off on start to prevent bad recognition on running autodarts-game
        broadcast({"on": False, "bri": EFFECT_BRIGHTNESS})
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
        # print(parsed_score)
    SCORE_AREA_EFFECTS = dict()
    for a in range(1, 13):
        parsed_score_area = parse_score_area_effects_argument(args["score_area_" + str(a) + "_effects"])
        SCORE_AREA_EFFECTS[a] = parsed_score_area
        # print(parsed_score_area)


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


    # https://stackoverflow.com/questions/11150343/slow-requests-on-local-flask-server
    app.run(host=HOST_IP, port=HOST_PORT, threaded=True)


    



   

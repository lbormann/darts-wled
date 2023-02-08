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
from flask import Flask, request
app = Flask(__name__)


BOGEY_NUMBERS = [169,168,166,165,163,162,159]
SUPPORTED_CRICKET_FIELDS = [15,16,17,18,19,20,25]
# 'Cricket'
SUPPORTED_GAME_VARIANTS = ['X01', 'Random Checkout']
WLED_STATE_PATH = '/json/state'
VERSION = '1.0.0'
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
        
        
def process_match_x01(msg):
    if msg['event'] == 'darts-thrown':
        # "player": currentPlayerName,
        # "game": {
        #     "mode": "X01",
        #     "pointsLeft": str(remainingPlayerScore),
        #     "dartNumber": "3",
        #     "dartValue": points,        
        # }

        val = msg['game']['dartValue']

        if HIGH_SCORE_ON != None and int(val) >= HIGH_SCORE_ON:
            effect_id = random.choice(HIGH_SCORE_EFFECT_IDS)
            highscore = {"bri": 255, "seg": {"fx": effect_id }}
            broadcast(highscore)
            printv('Highscore: ' + val + ' - Playing effect ' + str(effect_id))
        # ("score_" + val) in args
        elif args["score_" + val] != None and len(args["score_" + val]) >= 1:
            effect_id = random.choice(args["score_" + val])
            score = {"bri": 255, "seg": {"fx": effect_id}}
            broadcast(score)
            printv('Score: ' + val + ' Playing effect ' + str(effect_id))

        printv('darts-thrown')

    elif msg['event'] == 'darts-pulled':
        off = {"bri": 0}
        broadcast(off)
        printv('Darts-pulled')

    elif msg['event'] == 'busted':
        effect_id = random.choice(BUSTED_EFFECT_IDS)
        busted = {"bri": 255, "seg": {"fx": effect_id, "sx": 240, "ix": 240}}
        broadcast(busted)
        printv('Busted - Playing effect ' + str(effect_id))

    elif msg['event'] == 'game-won':
        # TODO: highfinish
        effect_id = random.choice(GAME_WON_EFFECT_IDS)
        gameWon = {"bri": 255, "seg": {"fx": effect_id}}
        broadcast(gameWon)
        printv('Game-won - Playing effect ' + str(effect_id))

    elif msg['event'] == 'match-won':
        # TODO: highfinish
        effect_id = random.choice(MATCH_WON_EFFECT_IDS)
        matchWon = {"bri": 255, "seg": {"fx": effect_id}}
        broadcast(matchWon)
        printv('Match-won - Playing effect ' + str(effect_id))

    elif msg['event'] == 'game-started':
        gameStarted = {"bri": 0}
        broadcast(gameStarted)
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

    ap.add_argument("-WEPS", "--wled_endpoints", required=True, nargs='+', help="Url(s) to wled instance(s)")
    ap.add_argument("-HSO", "--high_score_on", type=int, choices=range(1, 180), default=None, required=False, help="TODO")
    ap.add_argument("-HFO", "--high_finish_on", type=int, choices=range(1, 170), default=None, required=False, help="TODO")
    ap.add_argument("-G", "--game_won_effect_ids", type=int, choices=range(1, 117), default=None, required=False, nargs='*', help="WLED effect id(s) when game won occurs")
    ap.add_argument("-M", "--match_won_effect_ids", type=int, choices=range(1, 117), default=None, required=False, nargs='*', help="WLED effect id(s) when match won occurs")
    ap.add_argument("-B", "--busted_effect_ids", type=int, choices=range(1, 117), default=None, required=False, nargs='*', help="WLED effect id(s) when bust occurs")
    ap.add_argument("-HS", "--high_score_effect_ids", type=int, choices=range(1, 117), default=None, required=False, nargs='*', help="WLED effect id(s) when high-score occurs")
    ap.add_argument("-HF", "--high_finish_effect_ids", type=int, choices=range(1, 117), default=None, required=False, nargs='*', help="WLED effect id(s) when high-finish occurs")
    for v in range(0, 181):
        val = str(v)
        ap.add_argument("-S" + val, "--score_" + val, type=int, choices=range(1, 117), default=None, required=False, nargs='*', help="WLED effect id for score " + val)

    args = vars(ap.parse_args())

    WLED_ENDPOINTS = args['wled_endpoints']
    if WLED_ENDPOINTS is not None:
        parsedList = list()
        for e in WLED_ENDPOINTS:
            parsedList.append(parseUrl(e + WLED_STATE_PATH))
        WLED_ENDPOINTS = parsedList

    HIGH_SCORE_ON = args['high_score_on']
    HIGH_FINISH_ON = args['high_finish_on']
    GAME_WON_EFFECT_IDS = args['game_won_effect_ids']
    MATCH_WON_EFFECT_IDS = args['match_won_effect_ids']
    BUSTED_EFFECT_IDS = args['busted_effect_ids']
    HIGH_SCORE_EFFECT_IDS = args['high_score_effect_ids']
    HIGH_FINISH_EFFECT_IDS = args['high_finish_effect_ids']

    
    printv('Started with following arguments:')
    printv(json.dumps(args, indent=4))

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
    app.run(host='0.0.0.0', port='8081', threaded=True)


    



   

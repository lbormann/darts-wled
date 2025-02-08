# player-colors.py - Assigns colors to players in a match

PLAYER_COLOR_OPTIONS = list(['blue', 'red1', 'green', 'orange', 'purple', 'teal', 'magenta', 'yellow', 'limegreen', 'hotpink'])
PLAYER_ARGUMENTS_SEPARATOR = ','
PLAYER_COLOR_SEPARATOR = ':'
DEFAULT_PLAYER_COLOR_ASSIGNMENTS = dict()
MATCH_PLAYER_COLOR_ASSIGNMENTS = dict()

def parse_arguments(player_color_arguments):
    global DEFAULT_PLAYER_COLOR_ASSIGNMENTS
    
    if player_color_arguments == None:
        return player_color_arguments
    
    player_color_assignments = player_color_arguments.split(PLAYER_ARGUMENTS_SEPARATOR)

    DEFAULT_PLAYER_COLOR_ASSIGNMENTS = dict()

    for player_color_assignment in player_color_assignments:
        player_color_assignment_params = player_color_assignment.split(PLAYER_COLOR_SEPARATOR)
        player_name = player_color_assignment_params[0].strip()
        player_color = player_color_assignment_params[1].strip()

        DEFAULT_PLAYER_COLOR_ASSIGNMENTS[player_name] = player_color

    return DEFAULT_PLAYER_COLOR_ASSIGNMENTS



def assign(player_name):
    global MATCH_PLAYER_COLOR_ASSIGNMENTS

    if player_name in MATCH_PLAYER_COLOR_ASSIGNMENTS:
        return 
    else:
        MATCH_PLAYER_COLOR_ASSIGNMENTS[player_name] = PLAYER_COLOR_OPTIONS[len(MATCH_PLAYER_COLOR_ASSIGNMENTS)]



def reset_assignments():
    global MATCH_PLAYER_COLOR_ASSIGNMENTS

    MATCH_PLAYER_COLOR_ASSIGNMENTS = DEFAULT_PLAYER_COLOR_ASSIGNMENTS.copy()



def assign_match(msg):
    global MATCH_PLAYER_COLOR_ASSIGNMENTS
    host_player_id = msg['players'][0]['host']['id']
    match_players = msg['players']

    reset_assignments()
    host_player_is_in_players = False
    for player in match_players:
        if player['id'] == host_player_id:
            host_player_is_in_players = True
            break

    if not host_player_is_in_players:
        match_players.insert(0,msg['players'][0]['host'])

    for player in match_players:
        player_name = player['name']
        if MATCH_PLAYER_COLOR_ASSIGNMENTS.get(player["name"]) == None:
            assign(player_name)

    return MATCH_PLAYER_COLOR_ASSIGNMENTS



def get_next(msg):
    global MATCH_PLAYER_COLOR_ASSIGNMENTS

    if len(MATCH_PLAYER_COLOR_ASSIGNMENTS) == 0:
        MATCH_PLAYER_COLOR_ASSIGNMENTS = DEFAULT_PLAYER_COLOR_ASSIGNMENTS

    playerName = msg['player']

    if MATCH_PLAYER_COLOR_ASSIGNMENTS.get(playerName) is None:
        assign(playerName)

    nextColor = MATCH_PLAYER_COLOR_ASSIGNMENTS.get(playerName)

    return nextColor

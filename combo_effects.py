import logging

logger = logging.getLogger()


class ComboEffectTracker:
    """
    Tracks individual dart throws per player turn and checks for matching combo definitions.
    
    Combo definitions are parsed from the -CMB argument. Each combo consists of:
    - A sorted tuple of fieldNames (e.g. ('s1', 's20', 's5') -> sorted to ('s1', 's20', 's5'))
    - A list of ParsedWLEDEffect objects (random-choice if multiple)
    
    The tracker stores fieldNames per player per dart number. When darts-thrown fires,
    the sorted fieldNames are compared against all defined combos. On match, the combo
    effect is returned and takes priority over Score/Area effects.
    
    Tracking is reset on: darts-pulled, darts-thrown (after check), busted,
    game-won, match-won, game-started, match-started.
    """

    def __init__(self, combo_definitions=None, debug=False):
        """
        Args:
            combo_definitions: List of (sorted_fields_tuple, parsed_effects_list) or None
            debug: Enable debug logging
        """
        self.combo_definitions = combo_definitions
        self.debug = debug
        # {playerIndex: {dartNumber: fieldName}}
        self._current_turn = {}

    @property
    def is_active(self):
        return self.combo_definitions is not None and len(self.combo_definitions) > 0

    def track_throw(self, msg):
        """
        Tracks a single dart throw (dart1-thrown, dart2-thrown, dart3-thrown).
        Stores the fieldName indexed by dartNumber per player.
        Duplicate messages for the same dartNumber overwrite the previous value (safe).
        
        Args:
            msg: The data-feeder message dict containing game.fieldName, game.dartNumber, playerIndex
        """
        if not self.is_active:
            return

        player_idx = msg.get('playerIndex', '0')
        dart_number = str(msg['game']['dartNumber'])
        field_name = msg['game']['fieldName'].lower()

        if player_idx not in self._current_turn:
            self._current_turn[player_idx] = {}

        self._current_turn[player_idx][dart_number] = field_name

        if self.debug:
            current_fields = self._current_turn[player_idx]
            logger.info(f'  [DEBUG] Combo track: player={player_idx} dart#{dart_number}={field_name} (turn: {current_fields})')

    def check_combo(self, player_index):
        """
        Checks if the tracked darts for the given player match any combo definition.
        The thrown fieldNames are sorted and compared against combo definitions.
        
        Args:
            player_index: The playerIndex string (e.g. '0', '1')
            
        Returns:
            Tuple of (effects_list, combo_description_string) if match found, None otherwise
        """
        if not self.is_active:
            return None

        player_idx = player_index if player_index else '0'
        darts = self._current_turn.get(player_idx, {})

        if not darts:
            return None

        # Sort by dart number, then extract and sort fieldNames
        thrown_fields = tuple(sorted([darts[k] for k in sorted(darts.keys())]))

        if self.debug:
            logger.info(f'  [DEBUG] Combo check: player={player_idx} thrown={thrown_fields}')

        # Collect ALL matching combos (same fields can appear multiple times with different targets)
        merged_effects = []
        for (combo_fields, combo_effects) in self.combo_definitions:
            if thrown_fields == combo_fields:
                merged_effects.extend(combo_effects)

        if merged_effects:
            combo_desc = ','.join(thrown_fields)
            if self.debug:
                logger.info(f'  [DEBUG] Combo MATCH: {combo_desc} ({len(merged_effects)} effect(s))')
            return (merged_effects, combo_desc)

        if self.debug:
            logger.info(f'  [DEBUG] Combo: no match')

        return None

    def clear(self, player_index):
        """
        Clears the tracked darts for the given player.
        Called on: darts-pulled, darts-thrown (after check), busted,
        game-won, match-won, game-started, match-started.
        
        Args:
            player_index: The playerIndex string (e.g. '0', '1')
        """
        player_idx = player_index if player_index else '0'
        if player_idx in self._current_turn:
            if self.debug:
                logger.info(f'  [DEBUG] Combo clear: player={player_idx}')
            del self._current_turn[player_idx]

    def clear_all(self):
        """Clears tracking for all players. Used on match-started/game-started."""
        if self.debug and self._current_turn:
            logger.info(f'  [DEBUG] Combo clear all players')
        self._current_turn.clear()


def parse_combo_effects_argument(combo_args, parse_effects_fn):
    """
    Parses the -CMB argument into a list of combo definitions.
    
    Each string containing '=' starts a new combo definition.
    Strings without '=' are additional random-choice effects for the previous combo.
    
    Format: "field1,field2,field3=effect_definition"
    
    Examples:
        -CMB "s1,s20,s5=63|red"
        -CMB "s1,s20,s5=63|red" "102|blue"
        -CMB "s1,s20,s5=63|red" "t1,t1,t1=102|blue"
        -CMB "s1,s20,s5=63|red|e:0" "t1,t1,t1=102|blue|e:1"
    
    Args:
        combo_args: The raw argument list from argparse (list of strings or None)
        parse_effects_fn: The parse_effects_argument function to parse effect strings
        
    Returns:
        List of (sorted_fields_tuple, parsed_effects_list) or None
    """
    if combo_args is None:
        return None

    combos = []
    current_fields = None
    current_effects_raw = []

    for combo_str in combo_args:
        if '=' in combo_str:
            # Save previous combo if exists
            if current_fields is not None and current_effects_raw:
                parsed = parse_effects_fn(current_effects_raw)
                if parsed:
                    combos.append((current_fields, parsed))

            # Start new combo
            parts = combo_str.split('=', 1)
            fields_str = parts[0]
            effect_str = parts[1]
            current_fields = tuple(sorted([f.strip().lower() for f in fields_str.split(',')]))
            current_effects_raw = [effect_str]
        else:
            # Additional random-choice effect for current combo
            if current_fields is not None:
                current_effects_raw.append(combo_str)
            else:
                logger.info(f"[WARNING] Combo effect '{combo_str}' ignored - no field definition (missing 'fields=...' prefix)")

    # Save last combo
    if current_fields is not None and current_effects_raw:
        parsed = parse_effects_fn(current_effects_raw)
        if parsed:
            combos.append((current_fields, parsed))

    if not combos:
        return None

    # Log parsed combos
    logger.info(f'Combo effects configured: {len(combos)} combo(s)')
    for (fields, effects) in combos:
        logger.info(f'  - [{",".join(fields)}] -> {len(effects)} effect(s)')

    return combos

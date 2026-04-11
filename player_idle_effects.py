import logging

logger = logging.getLogger()


class PlayerIdleEffects:
    """
    Manages player-name-based idle effects configured via -PIDE argument.
    
    Each definition maps a player name to one or more WLED effects.
    Multiple definitions for the same player name are merged (random-choice).
    Supports multi-endpoint targeting via e: parameter.
    
    Falls back to None if no match is found, allowing the caller
    to use the default IDE/IDE2/IDE3... logic.
    """

    def __init__(self, player_idle_definitions=None, debug=False):
        """
        Args:
            player_idle_definitions: Dict of {player_name_lower: [ParsedWLEDEffect, ...]} or None
            debug: Enable debug logging
        """
        self.definitions = player_idle_definitions
        self.debug = debug

    @property
    def is_active(self):
        return self.definitions is not None and len(self.definitions) > 0

    def get_idle_effect(self, player_name):
        """
        Returns the idle effect list for the given player name, or None if not configured.
        
        Args:
            player_name: The player name string from the data feeder message
            
        Returns:
            List of ParsedWLEDEffect objects if found, None otherwise
        """
        if not self.is_active or not player_name:
            return None

        key = player_name.strip().lower()
        effects = self.definitions.get(key)

        if effects and self.debug:
            logger.info(f'  [DEBUG] PIDE match: player="{player_name}" -> {len(effects)} effect(s)')

        if not effects and self.debug:
            logger.info(f'  [DEBUG] PIDE: no match for player="{player_name}", using fallback')

        return effects


def parse_player_idle_effects_argument(pide_args, parse_effects_fn):
    """
    Parses the -PIDE argument into a dict of player-name -> effects.
    
    Each string containing '=' starts a new definition.
    Strings without '=' add random-choice effects to the previous definition.
    
    Format: "playername=effect_definition"
    
    Multiple definitions for the same player name are merged.
    
    Examples:
        -PIDE "john=solid|green"
        -PIDE "john=solid|green|e:0" "john=solid|blue|e:1"
        -PIDE "john=solid|green" "ps|5"  (random-choice for john)
        -PIDE "john=solid|green" "jane=solid|red"
    
    Args:
        pide_args: The raw argument list from argparse (list of strings or None)
        parse_effects_fn: The parse_effects_argument function to parse effect strings
        
    Returns:
        Dict of {player_name_lower: [ParsedWLEDEffect, ...]} or None
    """
    if pide_args is None:
        return None

    definitions = {}
    current_player = None
    current_effects_raw = []

    def _save_current():
        nonlocal current_player, current_effects_raw
        if current_player is not None and current_effects_raw:
            parsed = parse_effects_fn(current_effects_raw)
            if parsed:
                if current_player in definitions:
                    definitions[current_player].extend(parsed)
                else:
                    definitions[current_player] = parsed

    for arg_str in pide_args:
        if '=' in arg_str:
            # Save previous definition
            _save_current()

            # Start new definition
            parts = arg_str.split('=', 1)
            current_player = parts[0].strip().lower()
            effect_str = parts[1]
            current_effects_raw = [effect_str]
        else:
            # Additional random-choice effect for current player
            if current_player is not None:
                current_effects_raw.append(arg_str)
            else:
                logger.info(f"[WARNING] Player idle effect '{arg_str}' ignored - no player definition (missing 'player=...' prefix)")

    # Save last definition
    _save_current()

    if not definitions:
        return None

    return definitions

import logging

logger = logging.getLogger()


class DartMultiplierEffects:
    """
    Manages multiplier-based single-dart effects configured via the -DMU argument.

    Each definition maps either:
      - a generic multiplier (1, 2, 3) -> matches ANY dart with that fieldMultiplier
      - a specific fieldName (e.g. s20, d20, t20, d25, s25) -> matches that exact dart

    Multiple definitions for the same key are merged (random-choice).
    Supports multi-endpoint targeting (e:) and all standard effect options.

    Triggered ONLY on dart1-thrown / dart2-thrown / dart3-thrown events.
    Falls back to None if no match is found, allowing the caller to use the
    default -DS / -DSBULL logic (or skip entirely).

    Priority on lookup:
      1. Specific fieldName match (e.g. 't20')
      2. Generic multiplier match (e.g. '3')
    """

    def __init__(self, definitions=None, debug=False):
        """
        Args:
            definitions: Dict of {key: [ParsedWLEDEffect, ...]} or None.
                Keys are either '1'/'2'/'3' (generic multiplier) or
                lowercased fieldNames like 's20', 'd20', 't20', 'd25', 's25'.
            debug: Enable debug logging
        """
        self.definitions = definitions
        self.debug = debug

    @property
    def is_active(self):
        return self.definitions is not None and len(self.definitions) > 0

    def get_effect(self, field_name, field_multiplier):
        """
        Returns the effect list matching the given dart, or None if not configured.

        Args:
            field_name: The fieldName from the data feeder message (e.g. 's20', 't20').
            field_multiplier: The fieldMultiplier from the data feeder message (1, 2, 3).

        Returns:
            Tuple of (effects_list, match_key_string) if a match is found, else None.
        """
        if not self.is_active:
            return None

        # Build list of candidate keys for specific-field lookup.
        # Data feeder may send fieldName already prefixed ("s20", "t20", "d25")
        # OR as a bare number ("25" for outer bull, "50" for bullseye, "20" for s20).
        # We try the raw value first, then a prefixed variant derived from the multiplier,
        # plus the well-known bull aliases.
        candidate_keys = []
        if field_name is not None and str(field_name).strip() != '':
            raw = str(field_name).strip().lower()
            candidate_keys.append(raw)

            mult_str = str(field_multiplier).strip() if field_multiplier is not None else ''
            prefix_map = {'1': 's', '2': 'd', '3': 't'}
            prefix = prefix_map.get(mult_str)

            # If fieldName is purely numeric, build the prefixed variant (e.g. "25" + mult 1 -> "s25").
            if raw.isdigit() and prefix is not None:
                prefixed = f'{prefix}{raw}'
                if prefixed not in candidate_keys:
                    candidate_keys.append(prefixed)
                # Special-case bullseye: dartValue "50" with multiplier 2 maps to d25.
                if raw == '50':
                    if 'd25' not in candidate_keys:
                        candidate_keys.append('d25')
                if raw == '25' and prefix == 's':
                    # outer bull: also accept just "s25" (already handled above)
                    pass

        # 1. Specific field match (try all candidate spellings)
        for key in candidate_keys:
            effects = self.definitions.get(key)
            if effects:
                if self.debug:
                    logger.info(f'  [DEBUG] DMU specific match: field="{key}" -> {len(effects)} effect(s)')
                return (effects, key)

        # 2. Generic multiplier match
        if field_multiplier is not None and str(field_multiplier) != '':
            key = str(field_multiplier).strip()
            effects = self.definitions.get(key)
            if effects:
                if self.debug:
                    logger.info(f'  [DEBUG] DMU multiplier match: x{key} -> {len(effects)} effect(s)')
                return (effects, f'x{key}')

        if self.debug:
            logger.info(f'  [DEBUG] DMU: no match for field="{field_name}" multiplier="{field_multiplier}" (tried keys: {candidate_keys})')
        return None


def parse_dart_multiplier_effects_argument(dmu_args, parse_effects_fn):
    """
    Parses the -DMU argument into a dict of {key: [effects]}.

    Each string containing '=' starts a new definition.
    Strings without '=' add random-choice effects to the previous definition.

    Format: "<key>=effect_definition"

    Where <key> is one of:
      - '1', '2', '3'                       generic multiplier
      - 's1'..'s20', 's25'                  specific single field
      - 'd1'..'d20', 'd25'                  specific double field (d25 = bullseye)
      - 't1'..'t20'                         specific triple field

    Multiple definitions for the same key are merged into one random-choice pool.

    Examples:
        -DMU "3=ps|5"
        -DMU "1=solid|red" "2=solid|orange" "3=solid|green"
        -DMU "t20=63|red" "102|blue"
        -DMU "t20=63|red|e:0" "t20=102|blue|e:1"
        -DMU "3=ps|5" "t20=63|red"

    Args:
        dmu_args: The raw argument list from argparse (list of strings or None)
        parse_effects_fn: The parse_effects_argument function to parse effect strings

    Returns:
        Dict of {key: [ParsedWLEDEffect, ...]} or None
    """
    if dmu_args is None:
        return None

    # Robustness: when the user calls `-DMU=key1=eff1 key2=eff2` (single argparse token
    # with embedded spaces) we must split on whitespace as well. DMU effect tokens
    # never contain whitespace, so this is safe.
    flat_args = []
    for raw in dmu_args:
        if raw is None:
            continue
        for piece in str(raw).split():
            if piece:
                flat_args.append(piece)
    dmu_args = flat_args

    valid_multipliers = {'1', '2', '3'}
    valid_field_prefixes = ('s', 'd', 't')

    definitions = {}
    current_key = None
    current_effects_raw = []

    def _validate_key(raw_key):
        k = raw_key.strip().lower()
        if k in valid_multipliers:
            return k
        if len(k) >= 2 and k[0] in valid_field_prefixes:
            num_part = k[1:]
            if num_part.isdigit():
                num = int(num_part)
                if k[0] == 't' and 1 <= num <= 20:
                    return k
                if k[0] in ('s', 'd') and (1 <= num <= 20 or num == 25):
                    return k
        return None

    def _save_current():
        nonlocal current_key, current_effects_raw
        if current_key is not None and current_effects_raw:
            parsed = parse_effects_fn(current_effects_raw)
            if parsed:
                if current_key in definitions:
                    definitions[current_key].extend(parsed)
                else:
                    definitions[current_key] = parsed

    for arg_str in dmu_args:
        if '=' in arg_str:
            _save_current()
            parts = arg_str.split('=', 1)
            raw_key = parts[0]
            effect_str = parts[1]
            valid_key = _validate_key(raw_key)
            if valid_key is None:
                logger.info(f"[WARNING] Dart multiplier effect key '{raw_key}' is invalid - must be 1/2/3 or s<n>/d<n>/t<n>")
                current_key = None
                current_effects_raw = []
                continue
            current_key = valid_key
            current_effects_raw = [effect_str]
        else:
            if current_key is not None:
                current_effects_raw.append(arg_str)
            else:
                logger.info(f"[WARNING] Dart multiplier effect '{arg_str}' ignored - no key definition (missing 'key=...' prefix)")

    _save_current()

    if not definitions:
        return None

    logger.info(f'Dart multiplier effects configured: {len(definitions)} key(s)')
    for key, effects in definitions.items():
        logger.info(f'  - [{key}] -> {len(effects)} effect(s)')

    return definitions

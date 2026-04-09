from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


RANDOM_EFFECT_TOKEN = '__random__'


class EndpointTargetingError(ValueError):
    pass


@dataclass(frozen=True)
class EndpointTarget:
    indices: Optional[Tuple[int, ...]] = None

    @property
    def is_broadcast(self) -> bool:
        return self.indices is None

    @classmethod
    def broadcast(cls) -> "EndpointTarget":
        return cls(indices=None)

    @classmethod
    def parse(cls, raw_value: str, endpoint_count: Optional[int] = None) -> "EndpointTarget":
        if raw_value is None:
            return cls.broadcast()

        raw_value = raw_value.strip()
        if raw_value == '':
            raise EndpointTargetingError('Endpoint target must not be empty')

        indices = []
        for raw_index in raw_value.split(','):
            raw_index = raw_index.strip()
            if not raw_index.isdigit():
                raise EndpointTargetingError(f"Invalid endpoint index '{raw_index}'")

            index = int(raw_index)
            if endpoint_count is not None and index >= endpoint_count:
                raise EndpointTargetingError(
                    f'Endpoint index {index} is out of range for {endpoint_count} configured WLED endpoint(s)'
                )

            indices.append(index)

        if not indices:
            raise EndpointTargetingError('At least one endpoint index is required')

        return cls(indices=tuple(dict.fromkeys(indices)))


@dataclass(frozen=True)
class ParsedWLEDEffect:
    state: Dict
    duration: Optional[int] = None
    target: EndpointTarget = field(default_factory=EndpointTarget.broadcast)

    def clone_state(self) -> Dict:
        return deepcopy(self.state)

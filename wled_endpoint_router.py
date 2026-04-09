from typing import Any, Iterable, List


def normalize_wled_ws_url(endpoint: str) -> str:
    clean_host = endpoint.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '')
    clean_host = clean_host.rstrip('/ws').rstrip('/')
    return f'ws://{clean_host}/ws'


class WLEDEndpointRouter:
    def __init__(self, configured_endpoints: Iterable[str], websocket_endpoints: Iterable[Any]):
        self.configured_endpoints = list(configured_endpoints)
        self.websocket_endpoints = list(websocket_endpoints)

    def get_active_endpoints(self) -> List[Any]:
        active_endpoints = []
        for endpoint in self.websocket_endpoints:
            if hasattr(endpoint, 'sock') and endpoint.sock and endpoint.sock.connected:
                active_endpoints.append(endpoint)
        return active_endpoints

    def get_targeted_endpoints(self, endpoint_target, include_inactive: bool = False) -> List[Any]:
        available_endpoints = self.websocket_endpoints if include_inactive else self.get_active_endpoints()
        if endpoint_target is None or endpoint_target.is_broadcast:
            return list(available_endpoints)

        targeted_urls = {
            normalize_wled_ws_url(self.configured_endpoints[index])
            for index in endpoint_target.indices
        }
        return [endpoint for endpoint in available_endpoints if endpoint.url in targeted_urls]

    def describe_targets(self, endpoint_target) -> str:
        if endpoint_target is None or endpoint_target.is_broadcast:
            return ', '.join(self.configured_endpoints)

        selected = [self.configured_endpoints[index] for index in endpoint_target.indices]
        return ', '.join(f'#{index}={endpoint}' for index, endpoint in zip(endpoint_target.indices, selected))

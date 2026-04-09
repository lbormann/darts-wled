import json
import requests
import os
import hashlib
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

class WLEDDataManager:
    """
    Klasse zum Verwalten und Synchronisieren von WLED-Daten wie Effekte, Presets, Paletten etc.
    UnterstÃ¼tzt mehrere WLED-Endpoints mit separater Datenhaltung pro Endpoint.
    """
    
    def __init__(self, wled_endpoints: Union[str, List[str]], data_file_path: str = "wled_data.json"):
        """
        Initialisiert den WLED Data Manager
        
        Args:
            wled_endpoints: Einzelner WLED IP/Host (str) oder Liste von Endpoints
            data_file_path: Pfad zur JSON-Datei fÃ¼r gespeicherte Daten
        """
        if isinstance(wled_endpoints, str):
            wled_endpoints = [wled_endpoints]
        
        self.configured_endpoints = [self._normalize_endpoint(ep) for ep in wled_endpoints]
        self.primary_endpoint = self.configured_endpoints[0] if self.configured_endpoints else ""
        self.data_file_path = data_file_path
        self.wled_data = self._create_empty_data_structure()
    
    def _normalize_endpoint(self, endpoint: str) -> str:
        """Bereinigt einen Endpoint-String von Protokoll-Prefixen"""
        return endpoint.replace('ws://', '').replace('wss://', '').replace('http://', '').replace('https://', '').rstrip('/')
    
    def _create_empty_endpoint_data(self, endpoint: str) -> Dict[str, Any]:
        """Erstellt eine leere Datenstruktur fÃ¼r einen einzelnen Endpoint"""
        return {
            "endpoint": endpoint,
            "effects": {
                "names": [],
                "ids": []
            },
            "presets": {},
            "palettes": {
                "names": [],
                "ids": []
            },
            "info": {},
            "state": {},
            "segments": [],
            "data_hash": "",
            "last_updated": ""
        }
    
    def _create_empty_data_structure(self) -> Dict[str, Any]:
        """Erstellt die leere Multi-Endpoint-Datenstruktur"""
        endpoints = {}
        for ep in self.configured_endpoints:
            endpoints[ep] = self._create_empty_endpoint_data(ep)
        
        return {
            "schema_version": SCHEMA_VERSION,
            "primary_endpoint": self.primary_endpoint,
            "configured_endpoints": list(self.configured_endpoints),
            "endpoints": endpoints,
            "last_updated": ""
        }
    
    def _get_endpoint_data(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Gibt die Daten fÃ¼r einen bestimmten Endpoint zurÃ¼ck.
        Wenn kein Endpoint angegeben, wird der primÃ¤re Endpoint verwendet.
        """
        ep = self._normalize_endpoint(endpoint) if endpoint else self.primary_endpoint
        return self.wled_data.get("endpoints", {}).get(ep, self._create_empty_endpoint_data(ep))
    
    def _set_endpoint_data(self, endpoint: str, data: Dict[str, Any]):
        """Setzt die Daten fÃ¼r einen bestimmten Endpoint"""
        ep = self._normalize_endpoint(endpoint)
        if "endpoints" not in self.wled_data:
            self.wled_data["endpoints"] = {}
        self.wled_data["endpoints"][ep] = data
        
    def _make_request(self, path: str, endpoint: Optional[str] = None) -> Optional[Dict]:
        """
        Macht eine HTTP-Anfrage an einen WLED-Controller
        
        Args:
            path: API-Pfad (z.B. "/json/info")
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            JSON-Response oder None bei Fehler
        """
        target = endpoint if endpoint else self.primary_endpoint
        try:
            url = f"http://{target}{path}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von {path} von {target}: {e}")
            return None
    
    def fetch_effects(self, endpoint: Optional[str] = None) -> List[str]:
        """
        Holt alle verfÃ¼gbaren Effekte vom WLED-Controller
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Effekt-Namen
        """
        try:
            effects_data = self._make_request("/json/eff", endpoint)
            if effects_data:
                # Effekte bereinigen (@ und alles danach entfernen)
                effects = [effect.lower().split('@', 1)[0] for effect in effects_data]
                return effects
            return []
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Effekte: {e}")
            return []
    
    def fetch_palettes(self, endpoint: Optional[str] = None) -> List[str]:
        """
        Holt alle verfÃ¼gbaren Paletten vom WLED-Controller
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Paletten-Namen
        """
        try:
            palettes_data = self._make_request("/json/pal", endpoint)
            if palettes_data:
                return palettes_data
            return []
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Paletten: {e}")
            return []
    
    def fetch_presets(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Holt alle Presets vom WLED-Controller
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit Preset-Daten
        """
        try:
            presets_data = self._make_request("/presets.json", endpoint)
            if presets_data:
                return presets_data
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Presets: {e}")
            return {}
    
    def fetch_info(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Holt System-Informationen vom WLED-Controller
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit System-Informationen
        """
        try:
            info_data = self._make_request("/json/info", endpoint)
            if info_data:
                return info_data
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Informationen: {e}")
            return {}
    
    def fetch_state(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Holt den aktuellen Zustand vom WLED-Controller
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit Zustandsdaten
        """
        try:
            state_data = self._make_request("/json/state", endpoint)
            if state_data:
                return state_data
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Zustands: {e}")
            return {}
    
    def fetch_all_data(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Holt alle verfÃ¼gbaren Daten von einem WLED-Controller
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit allen WLED-Daten fÃ¼r diesen Endpoint
        """
        target = endpoint if endpoint else self.primary_endpoint
        logger.info(f"Lade WLED-Daten von {target}...")
        
        # Alle Daten abrufen
        effects = self.fetch_effects(target)
        palettes = self.fetch_palettes(target)
        presets = self.fetch_presets(target)
        info = self.fetch_info(target)
        state = self.fetch_state(target)
        
        # Effekt-IDs generieren
        effect_ids = list(range(len(effects))) if effects else []
        
        # Paletten-IDs generieren
        palette_ids = list(range(len(palettes))) if palettes else []
        
        # Segments aus State extrahieren
        segments = state.get('seg', []) if state else []
        
        # Aktuelle Daten zusammenstellen
        current_data = {
            "endpoint": target,
            "effects": {
                "names": effects,
                "ids": effect_ids
            },
            "presets": presets,
            "palettes": {
                "names": palettes,
                "ids": palette_ids
            },
            "info": info,
            "state": state,
            "segments": segments,
            "last_updated": self._get_current_timestamp()
        }
        
        # Hash fÃ¼r Ã„nderungserkennung berechnen
        current_data["data_hash"] = self._calculate_data_hash(current_data)
        
        return current_data
    
    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        Berechnet einen Hash der wichtigsten Daten fÃ¼r Ã„nderungserkennung
        
        Args:
            data: Daten-Dictionary
            
        Returns:
            MD5-Hash als String
        """
        # Nur relevante Daten fÃ¼r Hash verwenden (ohne Timestamps)
        hash_data = {
            "effects": data.get("effects", {"names": [], "ids": []}),
            "presets": data.get("presets", {}),
            "palettes": data.get("palettes", {"names": [], "ids": []}),
            "info": {k: v for k, v in data.get("info", {}).items() 
                    if k not in ["uptime", "time"]},  # Zeitbasierte Felder ausschlieÃŸen
        }
        
        hash_string = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _get_current_timestamp(self) -> str:
        """
        Gibt den aktuellen Timestamp zurÃ¼ck
        
        Returns:
            ISO-formatierter Timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _migrate_old_format(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migriert das alte Single-Endpoint-Format in das neue Multi-Endpoint-Format
        
        Args:
            old_data: Daten im alten Flat-Format
            
        Returns:
            Daten im neuen Multi-Endpoint-Format
        """
        old_endpoint = old_data.get("endpoint", self.primary_endpoint)
        normalized_ep = self._normalize_endpoint(old_endpoint)
        
        logger.info(f"Migriere altes WLED-Datenformat fÃ¼r Endpoint {normalized_ep}...")
        
        # Alte Daten als Endpoint-Eintrag Ã¼bernehmen
        endpoint_entry = {
            "endpoint": normalized_ep,
            "effects": old_data.get("effects", {"names": [], "ids": []}),
            "presets": old_data.get("presets", {}),
            "palettes": old_data.get("palettes", {"names": [], "ids": []}),
            "info": old_data.get("info", {}),
            "state": old_data.get("state", {}),
            "segments": old_data.get("segments", []),
            "data_hash": old_data.get("data_hash", ""),
            "last_updated": old_data.get("last_updated", "")
        }
        
        # Neue Struktur aufbauen
        endpoints = {normalized_ep: endpoint_entry}
        
        # FÃ¼r alle konfigurierten Endpoints leere EintrÃ¤ge anlegen, falls sie fehlen
        for ep in self.configured_endpoints:
            if ep not in endpoints:
                endpoints[ep] = self._create_empty_endpoint_data(ep)
        
        new_data = {
            "schema_version": SCHEMA_VERSION,
            "primary_endpoint": self.primary_endpoint,
            "configured_endpoints": list(self.configured_endpoints),
            "endpoints": endpoints,
            "last_updated": old_data.get("last_updated", "")
        }
        
        return new_data
    
    def load_data_from_file(self) -> bool:
        """
        LÃ¤dt gespeicherte Daten aus der JSON-Datei.
        Migriert automatisch das alte Single-Endpoint-Format.
        
        Returns:
            True wenn erfolgreich geladen, False sonst
        """
        try:
            if os.path.exists(self.data_file_path):
                with open(self.data_file_path, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                
                # Migration prÃ¼fen: Altes Format hat kein schema_version
                if "schema_version" not in loaded_data:
                    self.wled_data = self._migrate_old_format(loaded_data)
                    self.save_data_to_file()
                    logger.info(f"WLED-Daten aus {self.data_file_path} geladen und migriert")
                else:
                    self.wled_data = loaded_data
                    # Sicherstellen, dass neu konfigurierte Endpoints leere EintrÃ¤ge bekommen
                    for ep in self.configured_endpoints:
                        if ep not in self.wled_data.get("endpoints", {}):
                            if "endpoints" not in self.wled_data:
                                self.wled_data["endpoints"] = {}
                            self.wled_data["endpoints"][ep] = self._create_empty_endpoint_data(ep)
                    # Konfiguration aktualisieren
                    self.wled_data["configured_endpoints"] = list(self.configured_endpoints)
                    self.wled_data["primary_endpoint"] = self.primary_endpoint
                    logger.info(f"WLED-Daten aus {self.data_file_path} geladen")
                
                return True
            else:
                logger.info(f"Datei {self.data_file_path} existiert nicht")
                return False
        except Exception as e:
            logger.error(f"Fehler beim Laden der Datei {self.data_file_path}: {e}")
            return False
    
    def save_data_to_file(self, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Speichert Daten in die JSON-Datei
        
        Args:
            data: Zu speichernde Daten (wenn None, werden aktuelle wled_data verwendet)
            
        Returns:
            True wenn erfolgreich gespeichert, False sonst
        """
        try:
            save_data = data if data is not None else self.wled_data
            with open(self.data_file_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            logger.info(f"WLED-Daten in {self.data_file_path} gespeichert")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern in {self.data_file_path}: {e}")
            return False
    
    def check_for_changes(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        PrÃ¼ft ob sich WLED-Daten fÃ¼r einen Endpoint geÃ¤ndert haben
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit Informationen Ã¼ber Ã„nderungen
        """
        target = endpoint if endpoint else self.primary_endpoint
        
        # Aktuelle Daten vom WLED abrufen
        current_data = self.fetch_all_data(target)
        
        if not current_data.get("effects"):
            logger.warning(f"Keine aktuellen WLED-Daten fÃ¼r {target} verfÃ¼gbar")
            return {"has_changes": False, "error": f"Keine Daten von {target} verfÃ¼gbar"}
        
        # Gespeicherte Daten laden
        saved_data = self._get_endpoint_data(target)
        
        # Hash-Vergleich
        current_hash = current_data.get("data_hash", "")
        saved_hash = saved_data.get("data_hash", "")
        
        changes = {
            "has_changes": current_hash != saved_hash,
            "current_hash": current_hash,
            "saved_hash": saved_hash,
            "endpoint": target,
            "changes": {}
        }
        
        if changes["has_changes"]:
            logger.info(f"Ã„nderungen in WLED-Daten fÃ¼r {target} erkannt")
            
            # Detaillierte Ã„nderungen ermitteln
            changes["changes"] = self._compare_data_sections(saved_data, current_data)
            
            # Aktuelle Daten als neue gespeicherte Daten setzen
            self._set_endpoint_data(target, current_data)
            
        else:
            logger.info(f"Keine Ã„nderungen in WLED-Daten fÃ¼r {target}")
            
        return changes
    
    def _compare_data_sections(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """
        Vergleicht verschiedene Bereiche der WLED-Daten
        
        Args:
            old_data: Alte Daten
            new_data: Neue Daten
            
        Returns:
            Dictionary mit detaillierten Ã„nderungen
        """
        changes = {}
        
        # Effekte vergleichen
        old_effects = set(old_data.get("effects", {}).get("names", []))
        new_effects = set(new_data.get("effects", {}).get("names", []))
        if old_effects != new_effects:
            changes["effects"] = {
                "added": list(new_effects - old_effects),
                "removed": list(old_effects - new_effects),
                "total_old": len(old_effects),
                "total_new": len(new_effects)
            }
        
        # Presets vergleichen
        old_presets = old_data.get("presets", {})
        new_presets = new_data.get("presets", {})
        if old_presets != new_presets:
            changes["presets"] = {
                "old_count": len(old_presets),
                "new_count": len(new_presets),
                "changed": True
            }
        
        # Paletten vergleichen
        old_palettes = old_data.get("palettes", {}).get("names", [])
        new_palettes = new_data.get("palettes", {}).get("names", [])
        if old_palettes != new_palettes:
            changes["palettes"] = {
                "old_count": len(old_palettes),
                "new_count": len(new_palettes),
                "changed": True
            }
        
        # Info vergleichen (nur wichtige Felder)
        old_info = old_data.get("info", {})
        new_info = new_data.get("info", {})
        info_changed = False
        for key in ["ver", "name", "brand", "product", "leds"]:
            if old_info.get(key) != new_info.get(key):
                info_changed = True
                break
        
        if info_changed:
            changes["info"] = {"changed": True}
        
        return changes
    
    def sync_and_save(self) -> Dict[str, Any]:
        """
        Synchronisiert WLED-Daten fÃ¼r ALLE konfigurierten Endpoints und speichert sie
        
        Returns:
            Dictionary mit Sync-Informationen (inkl. endpoint_results pro Endpoint)
        """
        try:
            all_results = {}
            any_changes = False
            
            for ep in self.configured_endpoints:
                # Aktuelle Daten vom WLED abrufen
                current_data = self.fetch_all_data(ep)
                
                if not current_data.get("effects"):
                    logger.warning(f"Keine aktuellen WLED-Daten fÃ¼r {ep} verfÃ¼gbar")
                    all_results[ep] = {"has_changes": False, "endpoint": ep, "error": f"Keine Daten von {ep} verfÃ¼gbar"}
                    continue
                
                saved_data = self._get_endpoint_data(ep)
                
                # Erste Initialisierung fÃ¼r diesen Endpoint
                if not saved_data.get("data_hash"):
                    logger.info(f"Erste Initialisierung fÃ¼r Endpoint {ep}")
                    self._set_endpoint_data(ep, current_data)
                    all_results[ep] = {
                        "has_changes": True,
                        "first_init": True,
                        "endpoint": ep,
                        "changes": {
                            "effects": {
                                "total_new": len(current_data.get("effects", {}).get("names", [])),
                                "total_old": 0,
                                "added": current_data.get("effects", {}).get("names", []),
                                "removed": []
                            },
                            "presets": {
                                "new_count": len(current_data.get("presets", {})),
                                "old_count": 0
                            },
                            "palettes": {
                                "new_count": len(current_data.get("palettes", {}).get("names", [])),
                                "old_count": 0
                            }
                        }
                    }
                    any_changes = True
                else:
                    # Ã„nderungen prÃ¼fen per Hash-Vergleich
                    current_hash = current_data.get("data_hash", "")
                    saved_hash = saved_data.get("data_hash", "")
                    
                    if current_hash != saved_hash:
                        logger.info(f"Ã„nderungen in WLED-Daten fÃ¼r {ep} erkannt")
                        ep_changes = self._compare_data_sections(saved_data, current_data)
                        self._set_endpoint_data(ep, current_data)
                        all_results[ep] = {
                            "has_changes": True,
                            "endpoint": ep,
                            "changes": ep_changes
                        }
                        any_changes = True
                    else:
                        logger.info(f"Keine Ã„nderungen fÃ¼r {ep}")
                        all_results[ep] = {"has_changes": False, "endpoint": ep}
            
            # Globalen Timestamp aktualisieren
            self.wled_data["last_updated"] = self._get_current_timestamp()
            
            # Speichern wenn Ã„nderungen vorhanden
            if any_changes:
                success = self.save_data_to_file()
                if success:
                    logger.info("WLED-Daten erfolgreich synchronisiert und gespeichert")
                else:
                    logger.error("Fehler beim Speichern der synchronisierten Daten")
            else:
                success = True
                logger.info("Keine Synchronisation nÃ¶tig - Daten unverÃ¤ndert")
            
            # RÃ¼ckgabe: Aggregiertes Ergebnis, kompatibel mit bisherigem Format
            primary_result = all_results.get(self.primary_endpoint, {"has_changes": False})
            
            return {
                "has_changes": any_changes,
                "saved": any_changes and success,
                "endpoint_results": all_results,
                "changes": primary_result.get("changes", {}),
                "first_init": primary_result.get("first_init", False)
            }
            
        except Exception as e:
            logger.error(f"Fehler bei der Synchronisation: {e}")
            return {"has_changes": False, "error": str(e)}
    
    def get_effect_by_name(self, effect_name: str, endpoint: Optional[str] = None) -> Optional[int]:
        """
        Gibt die Effekt-ID fÃ¼r einen Effekt-Namen zurÃ¼ck
        
        Args:
            effect_name: Name des Effekts (case-insensitive)
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Effekt-ID oder None wenn nicht gefunden
        """
        ep_data = self._get_endpoint_data(endpoint)
        effects = ep_data.get("effects", {}).get("names", [])
        try:
            return effects.index(effect_name.lower())
        except ValueError:
            return None
    
    def get_available_effects(self, endpoint: Optional[str] = None) -> List[str]:
        """
        Gibt Liste aller verfÃ¼gbaren Effekte zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Effekt-Namen
        """
        return self._get_endpoint_data(endpoint).get("effects", {}).get("names", [])
    
    def get_effect_ids(self, endpoint: Optional[str] = None) -> List[int]:
        """
        Gibt Liste aller Effekt-IDs zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Effekt-IDs
        """
        return self._get_endpoint_data(endpoint).get("effects", {}).get("ids", [])
    
    def get_available_presets(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Gibt alle verfÃ¼gbaren Presets zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit Preset-Daten
        """
        return self._get_endpoint_data(endpoint).get("presets", {})
    
    def get_available_palettes(self, endpoint: Optional[str] = None) -> List[str]:
        """
        Gibt Liste aller verfÃ¼gbaren Paletten zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Paletten-Namen
        """
        return self._get_endpoint_data(endpoint).get("palettes", {}).get("names", [])
    
    def get_palette_ids(self, endpoint: Optional[str] = None) -> List[int]:
        """
        Gibt Liste aller Paletten-IDs zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Paletten-IDs
        """
        return self._get_endpoint_data(endpoint).get("palettes", {}).get("ids", [])
    
    def get_segments(self, endpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gibt alle verfÃ¼gbaren Segmente zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Liste der Segment-Daten
        """
        return self._get_endpoint_data(endpoint).get("segments", [])
    
    def get_segment_count(self, endpoint: Optional[str] = None) -> int:
        """
        Gibt die Anzahl der verfÃ¼gbaren Segmente zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Anzahl der Segmente
        """
        segments = self.get_segments(endpoint)
        return len(segments) if segments else 1
    
    def get_palette_by_name(self, palette_name: str, endpoint: Optional[str] = None) -> Optional[int]:
        """
        Gibt die Paletten-ID fÃ¼r einen Paletten-Namen zurÃ¼ck
        
        Args:
            palette_name: Name der Palette (case-insensitive)
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Paletten-ID oder None wenn nicht gefunden
        """
        ep_data = self._get_endpoint_data(endpoint)
        palettes = ep_data.get("palettes", {}).get("names", [])
        try:
            return palettes.index(palette_name.lower())
        except ValueError:
            return None
    
    def get_data_summary(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """
        Gibt eine Zusammenfassung der WLED-Daten fÃ¼r einen Endpoint zurÃ¼ck
        
        Args:
            endpoint: WLED-Host (wenn None, wird primary verwendet)
            
        Returns:
            Dictionary mit Daten-Zusammenfassung
        """
        ep_data = self._get_endpoint_data(endpoint)
        return {
            "endpoint": ep_data.get("endpoint", ""),
            "effects_count": len(ep_data.get("effects", {}).get("names", [])),
            "presets_count": len(ep_data.get("presets", {})),
            "palettes_count": len(ep_data.get("palettes", {}).get("names", [])),
            "last_updated": ep_data.get("last_updated", ""),
            "data_hash": ep_data.get("data_hash", "")
        }
    
    def get_all_endpoints_summary(self) -> List[Dict[str, Any]]:
        """
        Gibt Zusammenfassungen fÃ¼r alle konfigurierten Endpoints zurÃ¼ck
        
        Returns:
            Liste von Daten-Zusammenfassungen
        """
        return [self.get_data_summary(ep) for ep in self.configured_endpoints]

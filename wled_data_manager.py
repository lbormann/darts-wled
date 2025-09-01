import json
import requests
import os
import hashlib
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class WLEDDataManager:
    """
    Klasse zum Verwalten und Synchronisieren von WLED-Daten wie Effekte, Presets, Paletten etc.
    """
    
    def __init__(self, wled_endpoint: str, data_file_path: str = "wled_data.json"):
        """
        Initialisiert den WLED Data Manager
        
        Args:
            wled_endpoint: WLED IP/Host (z.B. "192.168.1.100")
            data_file_path: Pfad zur JSON-Datei für gespeicherte Daten
        """
        self.wled_endpoint = wled_endpoint.replace('ws://', '').replace('http://', '')
        self.data_file_path = data_file_path
        self.wled_data = {
            "endpoint": self.wled_endpoint,
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
        
    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """
        Macht eine HTTP-Anfrage an den WLED-Controller
        
        Args:
            endpoint: API-Endpoint (z.B. "/json/info")
            
        Returns:
            JSON-Response oder None bei Fehler
        """
        try:
            url = f"http://{self.wled_endpoint}{endpoint}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von {endpoint}: {e}")
            return None
    
    def fetch_effects(self) -> List[str]:
        """
        Holt alle verfügbaren Effekte vom WLED-Controller
        
        Returns:
            Liste der Effekt-Namen
        """
        try:
            effects_data = self._make_request("/json/eff")
            if effects_data:
                # Effekte bereinigen (@ und alles danach entfernen)
                effects = [effect.lower().split('@', 1)[0] for effect in effects_data]
                return effects
            return []
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Effekte: {e}")
            return []
    
    def fetch_palettes(self) -> List[str]:
        """
        Holt alle verfügbaren Paletten vom WLED-Controller
        
        Returns:
            Liste der Paletten-Namen
        """
        try:
            palettes_data = self._make_request("/json/pal")
            if palettes_data:
                return palettes_data
            return []
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Paletten: {e}")
            return []
    
    def fetch_presets(self) -> Dict[str, Any]:
        """
        Holt alle Presets vom WLED-Controller
        
        Returns:
            Dictionary mit Preset-Daten
        """
        try:
            presets_data = self._make_request("/presets.json")
            if presets_data:
                return presets_data
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Presets: {e}")
            return {}
    
    def fetch_info(self) -> Dict[str, Any]:
        """
        Holt System-Informationen vom WLED-Controller
        
        Returns:
            Dictionary mit System-Informationen
        """
        try:
            info_data = self._make_request("/json/info")
            if info_data:
                return info_data
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Informationen: {e}")
            return {}
    
    def fetch_state(self) -> Dict[str, Any]:
        """
        Holt den aktuellen Zustand vom WLED-Controller
        
        Returns:
            Dictionary mit Zustandsdaten
        """
        try:
            state_data = self._make_request("/json/state")
            if state_data:
                return state_data
            return {}
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Zustands: {e}")
            return {}
    
    def fetch_all_data(self) -> Dict[str, Any]:
        """
        Holt alle verfügbaren Daten vom WLED-Controller
        
        Returns:
            Dictionary mit allen WLED-Daten
        """
        logger.info(f"Lade WLED-Daten von {self.wled_endpoint}...")
        
        # Alle Daten abrufen
        effects = self.fetch_effects()
        palettes = self.fetch_palettes()
        presets = self.fetch_presets()
        info = self.fetch_info()
        state = self.fetch_state()
        
        # Effekt-IDs generieren
        effect_ids = list(range(len(effects))) if effects else []
        
        # Paletten-IDs generieren
        palette_ids = list(range(len(palettes))) if palettes else []
        
        # Segments aus State extrahieren
        segments = state.get('seg', []) if state else []
        
        # Aktuelle Daten zusammenstellen
        current_data = {
            "endpoint": self.wled_endpoint,
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
        
        # Hash für Änderungserkennung berechnen
        current_data["data_hash"] = self._calculate_data_hash(current_data)
        
        return current_data
    
    def _calculate_data_hash(self, data: Dict[str, Any]) -> str:
        """
        Berechnet einen Hash der wichtigsten Daten für Änderungserkennung
        
        Args:
            data: Daten-Dictionary
            
        Returns:
            MD5-Hash als String
        """
        # Nur relevante Daten für Hash verwenden (ohne Timestamps)
        hash_data = {
            "effects": data.get("effects", {"names": [], "ids": []}),
            "presets": data.get("presets", {}),
            "palettes": data.get("palettes", {"names": [], "ids": []}),
            "info": {k: v for k, v in data.get("info", {}).items() 
                    if k not in ["uptime", "time"]},  # Zeitbasierte Felder ausschließen
        }
        
        hash_string = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _get_current_timestamp(self) -> str:
        """
        Gibt den aktuellen Timestamp zurück
        
        Returns:
            ISO-formatierter Timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def load_data_from_file(self) -> bool:
        """
        Lädt gespeicherte Daten aus der JSON-Datei
        
        Returns:
            True wenn erfolgreich geladen, False sonst
        """
        try:
            if os.path.exists(self.data_file_path):
                with open(self.data_file_path, 'r', encoding='utf-8') as f:
                    self.wled_data = json.load(f)
                logger.info(f"WLED-Daten aus {self.data_file_path} geladen")
                return True
            else:
                logger.info(f"Datei {self.data_file_path} existiert nicht")
                return False
        except Exception as e:
            logger.error(f"Fehler beim Laden der Datei {self.data_file_path}: {e}")
            return False
    
    def save_data_to_file(self, data: Dict[str, Any] = None) -> bool:
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
    
    def check_for_changes(self) -> Dict[str, Any]:
        """
        Prüft ob sich WLED-Daten geändert haben und gibt Änderungen zurück
        
        Returns:
            Dictionary mit Informationen über Änderungen
        """
        # Aktuelle Daten vom WLED abrufen
        current_data = self.fetch_all_data()
        
        if not current_data.get("effects"):
            logger.warning("Keine aktuellen WLED-Daten verfügbar")
            return {"has_changes": False, "error": "Keine Daten verfügbar"}
        
        # Gespeicherte Daten laden
        saved_data = self.wled_data.copy()
        
        # Hash-Vergleich
        current_hash = current_data.get("data_hash", "")
        saved_hash = saved_data.get("data_hash", "")
        
        changes = {
            "has_changes": current_hash != saved_hash,
            "current_hash": current_hash,
            "saved_hash": saved_hash,
            "changes": {}
        }
        
        if changes["has_changes"]:
            logger.info("Änderungen in WLED-Daten erkannt")
            
            # Detaillierte Änderungen ermitteln
            changes["changes"] = self._compare_data_sections(saved_data, current_data)
            
            # Aktuelle Daten als neue gespeicherte Daten setzen
            self.wled_data = current_data
            
        else:
            logger.info("Keine Änderungen in WLED-Daten")
            
        return changes
    
    def _compare_data_sections(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """
        Vergleicht verschiedene Bereiche der WLED-Daten
        
        Args:
            old_data: Alte Daten
            new_data: Neue Daten
            
        Returns:
            Dictionary mit detaillierten Änderungen
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
        Synchronisiert WLED-Daten und speichert sie bei Änderungen
        
        Returns:
            Dictionary mit Sync-Informationen
        """
        try:
            # Aktuelle Daten vom WLED abrufen
            current_data = self.fetch_all_data()
            
            if not current_data.get("effects"):
                logger.warning("Keine aktuellen WLED-Daten verfügbar")
                return {"has_changes": False, "error": "Keine Daten verfügbar"}
            
            # Wenn noch keine Daten geladen wurden (erste Ausführung), alles als neu betrachten
            if not self.wled_data.get("data_hash"):
                logger.info("Erste Initialisierung - alle Daten werden gespeichert")
                self.wled_data = current_data
                success = self.save_data_to_file()
                return {
                    "has_changes": True,
                    "saved": success,
                    "first_init": True,
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
            
            # Änderungen prüfen
            change_info = self.check_for_changes()
            
            if change_info.get("has_changes", False):
                # Daten speichern wenn Änderungen vorhanden
                success = self.save_data_to_file()
                change_info["saved"] = success
                
                if success:
                    logger.info("WLED-Daten erfolgreich synchronisiert und gespeichert")
                else:
                    logger.error("Fehler beim Speichern der synchronisierten Daten")
            else:
                change_info["saved"] = False
                logger.info("Keine Synchronisation nötig - Daten unverändert")
                
            return change_info
            
        except Exception as e:
            logger.error(f"Fehler bei der Synchronisation: {e}")
            return {"has_changes": False, "error": str(e)}
    
    def get_effect_by_name(self, effect_name: str) -> Optional[int]:
        """
        Gibt die Effekt-ID für einen Effekt-Namen zurück
        
        Args:
            effect_name: Name des Effekts (case-insensitive)
            
        Returns:
            Effekt-ID oder None wenn nicht gefunden
        """
        effects = self.wled_data.get("effects", {}).get("names", [])
        try:
            return effects.index(effect_name.lower())
        except ValueError:
            return None
    
    def get_available_effects(self) -> List[str]:
        """
        Gibt Liste aller verfügbaren Effekte zurück
        
        Returns:
            Liste der Effekt-Namen
        """
        return self.wled_data.get("effects", {}).get("names", [])
    
    def get_effect_ids(self) -> List[int]:
        """
        Gibt Liste aller Effekt-IDs zurück
        
        Returns:
            Liste der Effekt-IDs
        """
        return self.wled_data.get("effects", {}).get("ids", [])
    
    def get_available_presets(self) -> Dict[str, Any]:
        """
        Gibt alle verfügbaren Presets zurück
        
        Returns:
            Dictionary mit Preset-Daten
        """
        return self.wled_data.get("presets", {})
    
    def get_available_palettes(self) -> List[str]:
        """
        Gibt Liste aller verfügbaren Paletten zurück
        
        Returns:
            Liste der Paletten-Namen
        """
        return self.wled_data.get("palettes", {}).get("names", [])
    
    def get_palette_ids(self) -> List[int]:
        """
        Gibt Liste aller Paletten-IDs zurück
        
        Returns:
            Liste der Paletten-IDs
        """
        return self.wled_data.get("palettes", {}).get("ids", [])
    
    def get_segments(self) -> List[Dict[str, Any]]:
        """
        Gibt alle verfügbaren Segmente zurück
        
        Returns:
            Liste der Segment-Daten
        """
        return self.wled_data.get("segments", [])
    
    def get_segment_count(self) -> int:
        """
        Gibt die Anzahl der verfügbaren Segmente zurück
        
        Returns:
            Anzahl der Segmente
        """
        segments = self.get_segments()
        return len(segments) if segments else 1
    
    def get_palette_by_name(self, palette_name: str) -> Optional[int]:
        """
        Gibt die Paletten-ID für einen Paletten-Namen zurück
        
        Args:
            palette_name: Name der Palette (case-insensitive)
            
        Returns:
            Paletten-ID oder None wenn nicht gefunden
        """
        palettes = self.wled_data.get("palettes", {}).get("names", [])
        try:
            return palettes.index(palette_name.lower())
        except ValueError:
            return None
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        Gibt eine Zusammenfassung der WLED-Daten zurück
        
        Returns:
            Dictionary mit Daten-Zusammenfassung
        """
        return {
            "endpoint": self.wled_data.get("endpoint", ""),
            "effects_count": len(self.wled_data.get("effects", {}).get("names", [])),
            "presets_count": len(self.wled_data.get("presets", {})),
            "palettes_count": len(self.wled_data.get("palettes", {}).get("names", [])),
            "last_updated": self.wled_data.get("last_updated", ""),
            "data_hash": self.wled_data.get("data_hash", "")
        }

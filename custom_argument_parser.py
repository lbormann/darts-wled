"""
Custom ArgumentParser für bessere Fehlerausgabe
Zeigt nur die relevante Fehlermeldung statt der kompletten Hilfe
"""

import argparse
import sys


class CustomArgumentParser(argparse.ArgumentParser):
    """
    Erweiterter ArgumentParser mit verbesserter Fehlerausgabe.
    Zeigt bei ungültigen Argumenten nur die Fehlermeldung und 
    hilfreiche Hinweise, nicht die komplette Hilfe-Ausgabe.
    """
    
    def error(self, message):
        """
        Überschreibt die Standard-Fehlermeldung von ArgumentParser.
        
        Args:
            message (str): Die Fehlermeldung von argparse
        """
        # Header
        print('\n' + '='*70)
        print('ERROR: Invalid argument configuration')
        print('='*70)
        
        # Hauptfehlermeldung
        print(f'\n{message}')
        
        # Hilfreiche Hinweise basierend auf der Fehlermeldung
        print('\n' + '-'*70)
        print('Common issues:')
        print('-'*70)
        
        if 'required' in message.lower():
            print('  ✗ Missing required argument(s)')
            print('    → Required: -WEPS <wled_endpoint>')
            print('    → Example: -WEPS 192.168.1.100')
        
        if 'invalid' in message.lower() or 'choice' in message.lower():
            print('  ✗ Invalid value for argument')
            print('    → -DU: must be integer (e.g., -DU 5)')
            print('    → -BRI: must be 1-255 (e.g., -BRI 175)')
            print('    → -HFO: must be 1-170 (e.g., -HFO 100)')
            print('    → -DEB, -BSW, -OFF, -SOFF: must be 0 or 1')
        
        if 'unrecognized' in message.lower():
            print('  ✗ Unknown argument detected')
            print('    → Check for typos in argument names')
            print('    → Arguments are case-sensitive')
        
        # Fußzeile
        print('-'*70)
        print('\n💡 Use -h or --help to see all available arguments')
        print('💡 Check your command line for typos or missing values')
        print('='*70 + '\n')
        
        # Beende mit Error-Code 2 (Standard für ArgumentParser)
        sys.exit(2)
    
    def format_help(self):
        """
        Behält die Standard-Hilfe-Formatierung bei, wenn -h/--help verwendet wird.
        """
        return super().format_help()

## b1.11.0.7
- add `-DMU` argument: per-dart multiplier effects (1/2/3) and field-specific effects (e.g. t20, d25), triggered on dart1/2/3-thrown. Supports multi-endpoint targeting and random-choice. Always overridden by Score/Combo/Busted/Game-Won/Match-Won/High-Finish. Documented in Readme.md.

## b1.11.0.6
- Bugfix: build routine to avoid race conditions.

## b1.11.0.5
- add Multidevicesupport for more then one endpoint. Documented in Readme.md
- improved WLED Data Manager with endpoint-specific caching and automatic LED count detection
- add SLEEP effect which can be activated after a configurable idle time. Activated with -SLE and -SLET arguments
- add SLEOFF argument to configure the duration until WLED is turned off after entering sleep mode
- removed mirror messages out of log. 
- add playername specific IDLE effects with PIDE Argument 

## v1.10.4
- Bugfix: Speed (sx), Intensity (ix) and Palette (pal) parameters are now correctly sent as integer values to WLED

## v1.10.3
- bugfix Brightness not working

## v1.10.2
- bugfix takeout effekt

## v1.10.0
- Bugfix endpoint reconects


### b1.9.3
- Fixed segment handling when switching from multi-segment presets to color/effect control
- All segments except segment 0 are now properly deactivated
- Segment 0 is completely recreated with clean default values
- Layout fields (grouping, spacing, offset) are explicitly reset to defaults
- Only effect-specific fields are preserved from the command
- Endpoint-specific LED count management
- Each WLED controller now uses its own LED count for segment configuration
- LED counts are cached per endpoint for improved performance
- Automatic LED count detection on connection
- Improved thread management and reconnect behavior
- Old WebSocket threads are properly closed before creating new connections
- Thread-safe reconnect mechanism prevents duplicate connection attempts
- Daemon threads prevent zombie processes
- Named threads for better debugging (e.g., "WLED-192.168.1.144")
- Enhanced error handling
- Better validation of empty effect lists to prevent IndexError
- Improved debug output for segment operations
- More detailed error messages showing affected configuration 

### b1.9.1
- reconnect behaviour changes. 
       - improved stability

### b1.9.0
- stability "improvements"
- more Debug possibility
- changed default value for BSW to off

### b1.9.4
- Bugfix endpoint reconects


## b1.9.3
- Fixed segment handling when switching from multi-segment presets to color/effect control
  - All segments except segment 0 are now properly deactivated
  - Segment 0 is completely recreated with clean default values
  - Layout fields (grouping, spacing, offset) are explicitly reset to defaults
  - Only effect-specific fields are preserved from the command
- Endpoint-specific LED count management
  - Each WLED controller now uses its own LED count for segment configuration
  - LED counts are cached per endpoint for improved performance
  - Automatic LED count detection on connection
- Improved thread management and reconnect behavior
  - Old WebSocket threads are properly closed before creating new connections
  - Thread-safe reconnect mechanism prevents duplicate connection attempts
  - Daemon threads prevent zombie processes
  - Named threads for better debugging (e.g., "WLED-192.168.1.144")
- Enhanced error handling
  - Better validation of empty effect lists to prevent IndexError
  - Improved debug output for segment operations
  - More detailed error messages showing affected configuration 

## b1.9.1
- reconnect behaviour changes. 
       - improved stability

## b1.9.1
- reconnect behaviour changes. 
       - improved stability

## b1.9.0
- stability "improvements"
- more Debug possibility
- changed default value for BSW to off

## 1.8.3
- new WLED Data Manager for improved performance and data caching
- automatic multi-segment support - effects now apply to all active segments
- enhanced WLED data synchronization with change detection
- improved error handling and logging for WLED communication
- cached WLED effects, presets, and palettes for faster startup
- automatic segment count detection and configuration

## 1.8.2
- some backend changes

## 1.8.1
- Bugfix -DU and playeridle conflict
- Caller Version min 2.17.11 Required!!!!!

## 1.8.0
- improved ATC, RTW, Chricket, Bermuda, tactics
- add -SOFF argument to turn off the lights when WLED controller is connected!
- -IDLE2 -IDLE6 different player colors for up to 6 players

## 1.7.3
- improved ATC, RTW, Chricket, Bermuda, tactics
- add -SOFF argument to turn off the lights when WLED controller is connected!

## 1.7.1
 - added Gamemodes

## 1.7.0
 - add connection information for caller
 - possibility to set effects for every dart
   by setting -DSxx and -DSBULL. Just optional feature

## 1.6.0
 - add -BSE Board stop effect
        possibility to set effect when the board stops during the match
 - add -TE Takeout effect
        posibillity to set effect when you takeout the darts or takeout is wrongly triggert
 - add -CE calibration effect
        possibility to set effect which will be used when calibration is in progress
 - add -OFF wled off
        possibility to turn WLED off after match has ended

## 1.5.3
- bugfix board takeout freeze after winning the match with arg -BSW set to 0
- set -BSW to default true

## 1.5.2

- add --BSW Arg to make it posible to activate/deactivate Bord Stop after win

## 1.5.0

- rename application to darts-wled


## 1.4.15

- switch to socketio-client


## 1.4.14

- fix ws bug


## 1.4.13

- add wss support


## 1.4.12

- hotfix messages


## 1.4.11

- add lobby-events (-PJ / --player_joined_effects & -PJ / --player_left_effects)


## 1.4.10

- add CHANGELOG
- add BACKLOG


## 0.0.0

- create receiver-endpoint
- support events with multiple effects that chosen randomly
- send events to wled-instance(s)
- Random Effect if user enters 'x' as argument value for effect-id
- add high-finish logic
- initial check is wled reachable download effect-names. (maybe turn on wled-installation(s) for 10 Seconds)
- let user choose between effect-index and effect-name in arguments
- support customizung effect-parameters
- support point-areas
- brightness configurable
- default effect when idle
- try to fix change-too-slow problem (WLED)
- support presets + playlists
- add wled-vars: speed, intensity, palette
- improve Readme: explain arguments, add example for starting app
- connect to data-feeder by websocket
- only process ws-msgs of first wled-endpoint
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
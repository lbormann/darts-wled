# DARTS-WLED
[![Downloads](https://img.shields.io/github/downloads/lbormann/darts-wled/total.svg)](https://github.com/lbormann/darts-wled/releases/latest)

Darts-wled controls your wled-installation(s) https://github.com/Aircoookie/WLED accordingly to the state of an https://autodarts.io game. A running instance of https://github.com/lbormann/darts-caller is needed that sends thrown points from https://autodarts.io to this application.


## COMPATIBILITY

| Variant | Support |
| ------------- | ------------- |
| X01 | :heavy_check_mark: |
| Cricket | :heavy_check_mark: |
| Bermuda | |
| Shanghai | |
| Gotcha | |
| Around the Clock | |
| Round the World | |
| Random Checkout | :heavy_check_mark: |
| Count Up | |
| Segment Training | |

## Showcase

#### Videos (Click to play):
[![IMAGE_ALT](https://img.youtube.com/vi/fDXomw55vhI/hqdefault.jpg)](https://youtu.be/fDXomw55vhI)

#### Images:
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/1.jpg?raw=true">
<p float="left">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/2.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/3.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/4.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/5.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/6.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/7.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/8.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/9.jpg?raw=true" width="49%">
<img src="https://github.com/lbormann/darts-wled/blob/main/showcase/10.jpg?raw=true" width="49%">
</p>

## Best working and looking LED-Location

To find the best possible light-impression without causing problem to dart-recognition algorithmn, I tried different led-stripe positions: 
1. As main lighting (in a plasma lighting ring): It`s way too dark - ugly as my surround is black (It should be definitely better with a white one).
2. Around the plasma lighting ring (outside): Not really a light-effect at all, as light has nothing to shine at.
3. Around my surround: Works best and looks nice! But you need a bright background/wall.

I`ve tested 1.) with a white surround. It looks OK, but the recognition algorithmn can NOT handle this: When a led-effect is played it does not recognize pulling.. after pressing next to end the turn, the recognition stops completely and you need to restart your board.. To avoid this you can stop the board right after darts are thrown, play an effect and start the board again right after the effect ended. (Use a combination of arguments 'DU' and 'BSS' to accomplish this).

Moreover as a general impression: If the leds are too far away from wall the effect is not good. More far away = more bad - just ez like that.
In my experience the primary factor causing false-positive recognitions is an excessive high led-brightness; you should limit your leds to a certain power draw (ex. 2000 mA).

Here is my currrent Hardware-Setup (You can google prices yourself):
* Controller: 1x AZDelivery ESP32 D1 Mini
* Led-stripe: 1x BTF-Lighting SK6812 RGBNW 60leds/m - ~ 4.6m used (2m for the surround)
* Power adapter: 1x Mean Well LPV-100-5 60W 5V DC
* Cosmetic: 1x fowong 2m Selbstklebend Dichtungsband 12mm(B) x 12mm(D) x 4m(L) Schaumstoffband (to prevent visible leds)
* Connector: 4x Wago 221-612 Verbindungsklemme 2 Leiter mit Betätigungshebel 0,5-6 qmm (to easily connect cables)
* Connector: 2x 3 Pin LED Anschluss 10 mm Lötfreier LED Licht Anschluss (to easily connect led-stripe segments)



## INSTALL INSTRUCTION

### Desktop-OS: 

- If you're running a desktop-driven OS it's recommended to use [darts-hub](https://github.com/lbormann/darts-hub) as it takes care of starting, updating, configurating and managing multiple apps.


### Headless-OS:

- Download the appropriate executable in the release section.


### By Source: 

#### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip.


#### Get the project

    git clone https://github.com/lbormann/darts-wled.git

Go to download-directory and type:

    pip3 install -r requirements.txt



## RUN IT

### Prerequisite

* You need to have a running caller - https://github.com/lbormann/darts-caller - (latest version)
* You need to have a running WLED-Installation (0.11.0 at minimum required)

### Run by executable

#### Example: Windows 

Create a shortcut of the executable; right click on the shortcut -> select properties -> add arguments in the target input at the end of the text field.

Example: C:\Downloads\darts-wled.exe -WEPS "your-first-wled-ip" "your-second-wled-ip"

Save changes.
Click on the shortcut to start the application.


### Run by source

#### Example: Linux

    python3 darts-wled.py -WEPS "your-wled-ip"



### Arguments

- -CON / --connection [OPTIONAL] [Default: "127.0.0.1:8079"] 
- -WEPS / --wled_endpoints [REQUIRED] [MULTIPLE ENTRIES POSSIBLE] 
- -DU / --effect_duration [OPTIONAL] [Default: 0]
- -BSS / --board_stop_start [OPTIONAL] [Default: 0.0]
- -BRI / --effect_brightness [OPTIONAL] [Default: 175] [Possible values: 1 .. 255] 
- -HFO / --high_finish_on [OPTIONAL] [Default: None] [Possible values: 2 .. 170] 
- -HF / --high_finish_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -IDE / --idle_effect [OPTIONAL] [Default: "solid|lightgoldenrodyellow"] [Possible values: See below] 
- -G / --game_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -M / --match_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -B / --busted_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -PJ / --player_joined_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -PL / --player_left_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -S{0-180} / --score_{0-180}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -A{1-12} / --score_area_{1-12}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below]
- -BSW / --board_stop_after_win [OPTIONAL] [Default: 1]
- -BSE / --board_stop_effect [OPTIONAL] [Default: None] [Possible values: See below] 
- -TE / --takeout_effect [OPTIONAL] [Default: None] [Possible values: See below] 
- -CE / --calibration_effect [OPTIONAL] [Default: None] [Possible values: See below]
- -DS{1-20} / --dart_score_{1-20}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -DSBULL / --dart_score_BULL_effects [OPTIONAL] [Default: None] [Possible values: See below]



*`-CON / --connection`*

Host address to data-feeder (darts-caller). By Default this is '127.0.0.1:8079' (means your local ip-address / usually you do NOT need to change this)
    
*`-WEPS / --wled_endpoints`*

IP to your WLED. You can define multiple entries. For example: '192.168.3.200' '192.168.3.201'. It is important to say that in case of multiple endpoints, the first one is treated as your primary endpoint which means
it will be used to check if is idle state is returned. Moreover if you drive multiple WLEDS make sure you disable WLEDs Sync function.

*`-DU / --effect_duration`*

Duration (in seconds), after a triggered effect/preset/playlist will return to idle-effect. By default this is '0' (infinity duration = return to idle happens when you pull your darts)

*`-BSS / --board_stop_start`*

The app stops your board after thrown darts. When duration (-DU) pasts wled returns to idle and starts the board: Value '0.0' means no "stop-start" at all; values greater '0.0' declare how long the start should be delayed. For instance a value '0.3' delays the board-start for one third of second after wled switched back to idle. You can play around with that. In my tests '0.4' was an appropriate value.

*`-BRI / --effect_brightness`*

Brightness for WLED-effects. You can choose a value between '1' and '255'. By default this is 175.

*`-HFO / --high_finish_on`*

Define what a highfinish means for you. Choose a score-value between '2' and '170'. This value is relevant for argument '-HF'. By default this is not set = no effects for 'Highfinishes'.

*`-HF / --high_finish_effects`*

Controls your wled(s) when a high-finish occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-IDE / --idle_effect`*

Controls your wled(s) when dart-pulling occurs or a configurated duration pasts.
Define an effect/preset/playlist that gets triggered. For examples see below!

*`-G / --game_won_effects`*

Controls your wled(s) when a game won occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-M / --match_won_effects`*

Controls your wled(s) when a match won occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-B / --busted_effects`*

Controls your wled(s) when a bust occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-PJ / --player_joined_effects`*

Controls your wled(s) when a player-join occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-PL / --player_left_effects`*

Controls your wled(s) when a player-left occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-S{0-180} / --score_{0-180}_effects`*

Controls your wled(s) when a specific score occurs. You can define every score-value between 0 and 180.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-A{1-12} / --score_area_{1-12}_effects`*

Besides the definition of single score-values you can define up to 12 score-areas.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-BSW / --board_stop_after_win`*
Controles board stop behaviour after win. When activated, the board will be stoped after winning Leg or match

*`-BSE / --board_stop_effect`*
Controls your wled(s) when a board stop occurs during the match.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-TOE / --takeout_effect`*
Controls your wled(s) when a takeout will be performed or is wrongly triggered.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-CE / --calibration_effect`*
Controls your wled(s) when calibration will be performed.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

*`-OFF / --wled_off`*
Controls your wled(s) and turns it off when match has ended.
1/true will activate the feature

*`-DS{1-20} / --dart_score_{1-20}_effects`*
Controls your wled(s) when a specific score for single darts occurs. You can define every score-value between 1 and 20.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!
--call_single_dart must be set for the caller

*`-DSBULL / --dart_score_BULL_effects`*
Controls your wled(s) when Bull or single bull was thrown. You can define every score-value between 1 and 20.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!
--call_single_dart must be set for the caller



_ _ _ _ _ _ _ _ _ _


#### Examples: 


| Argument | [condition] | effect 1 | effect 2 | effect 3 | ... |
| --  | -- | -- | --  | -- | -- | 
|-B |  | solid\\|red1 | solid\\|blue2 | | | |
|-A1 | 0-15 | 1\\|s255\\|i255\\|green1\\|red2 | solid\\|red1 | breathe\\|yellow1\\|blue2\\|s170\\|i40 | | |
|-A2 | 16-60 | ps\\|3 | | | 

The first argument-definition shows the event 'Busted': Busting will result in playing one of the 2 defined effects: solid (red) and solid (blue).

The second argument-definition shows a 'score-area': recognized scores between 0 and 15 will result in playing one of the 3 effects: blink (ID: 1), breathe or solid. For every of those effects we defined different colors, speeds and intensities; only the effect-name/effect-ID is required; everything else is an option.

The third argument-definition shows a 'score-area': recognized scores between 16 and 60 result in playing preset (or playlist) 3.

* To set a preset or playlists, use the displayed ID in WLED! Moreover you can set a custom duration (Except -IDE)

    syntax: **"ps|{ID}|{seconds}"**

* To set an effect, use an wled-effect-name or the corresponding ID (https://github.com/Aircoookie/WLED/wiki/List-of-effects-and-palettes):

    syntax: **"{'effect-name' or 'effect-ID'}|{primary-color-name}|{secondary-color-name}|{tertiary-color-name}"**

* To set effect- speed, intensity, palette, duration (Except -IDE)

    syntax: **"{'effect-name' or 'effect-ID'}|s{1-255}|i{1-255}|p{palette-ID}|d{seconds}"**

* For color-name usage, validate that the color-name you want is available in the list!

    validate here: **https://github.com/lbormann/darts-wled/blob/main/colors.txt**

* To set an random effect, use 'x' or 'X' as effect-id

    syntax: **"x"**

* If don't understand have a look at the example file!

    learn at: **start.bat**




## Community-Profiles

| Argument | Tullaris#4778 | wusaaa#0578 | Sini#8190
| --  | -- | -- | -- |
| HF (Highfinish) | fire flicker | 4 87 26 29 93 42 64 | ps\\|1 ps\\|2 |
| IDE (Idle) | solid\\|lightgoldenrodyellow | solid\\|lightgoldenrodyellow | ps\\|10 |
| G (Game-won) | colorloop | 4 87 26 29 93 42 64 | ps\\|9 ps\\|11 |
| M (Match-won) | running\\|orange\\|red1 | 4 87 26 29 93 42 64 | ps\\|3 ps\\|4 |
| B (Busted) | fire 2012 | solid\\|red1 | ps\\|20 ps\\|21 |
| S0 (score 0) | breathe\\|orange\\|red1 | | ps\\|5 ps\\|6 |
| S3 (Score 3) | running | | |
| S26 (Score 26) | dynamic | | ps\\|7 ps\\|8 |
| S135 (Score 135) | | 78 9 | |
| S140 (Score 140) | | 81 | |
| S144 (Score 144) | | 78 9 | |
| S153 (Score 153) | | 78 9 | |
| S162 (Score 162) | | 78 9 | |
| S171 (Score 171) | | 78 9 | |
| S180 (Score 180) | rainbow | 78 9 | ps\\|12 ps\\|13 |
| A1 (Area 1) | 0-14 solid\\|deeppink1 | 0-30 solid\\|orange | 0-25 ps\\|14 ps\\|15 |
| A2 (Area 2) | 15-29 solid\\|blue | 31-60 solid\\|orange1 | 27-59 ps\\|16 ps\\|18 |
| A3 (Area 3) | 30-44 solid\\|deepskyblue1 | 61-90 solid\\|yellow1 | 60-99 ps\\|17 ps\\|19 |
| A4 (Area 4) | 45-59 solid\\|green | 91-120 solid\\|olivedrab4 | 100-179 ps\\|22 ps\\|23 |
| A5 (Area 5) | 60-74 solid\\|chartreuse1 | 121-150 solid\\|olivedrab1 | |
| A6 (Area 6) | 75-89 solid\\|brick | | |
| A7 (Area 7) | 90-104 solid\\|tomato1 | | |
| A8 (Area 8) | 105-119 solid\\|tan1 | | |
| A9 (Area 9) | 120-134 solid\\|yellow1 | | |
| A10 (Area 10) | 135-149 solid\\|purple1 | | |
| A11 (Area 11) | 150-164 solid\\|orange | | |
| A12 (Area 12) | 165-180 solid\\|red1 | | |

Moreover you can find ready-to-go wled-presets in the community-folder; You can restore a preset-file in wled-ui.



## !!! IMPORTANT !!!

This application requires a running instance of darts-caller https://github.com/lbormann/darts-caller


## LAST WORDS

Make sure your wled(s) are working ;)
Thanks to Timo for awesome https://autodarts.io. It will be huge!


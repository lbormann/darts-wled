# AUTODARTS-WLED

Autodarts-wled controls your wled-installation(s) https://github.com/Aircoookie/WLED accordingly to the state of an https://autodarts.io game. A running instance of https://github.com/lbormann/autodarts-caller is needed that sends the thrown points from https://autodarts.io to this application.

Tested on Windows 10 & 11 Pro x64, Python 3.9.7, 
WLED-Installation 0.14.0-b1 (0.11.0 at minimum required) (LED-Stripe SK6812 RGBNW 60leds/m - 4,4 meters powered by a 60W power adapter running on an ESP32 D1 Mini)


## COMPATIBILITY

x = supported
o = not (yet) supported

| Variant | Support |
| ------------- | ------------- |
| X01 | x |
| Cricket | x |
| Bermuda | o |
| Shanghai | o |
| Gotcha | o |
| Around the Clock | o |
| Round the World | o |
| Random Checkout | x |
| Count Up | o |

## Showcase

![sc1](https://github.com/lbormann/autodarts-wled/blob/main/showcase/1.jpg?raw=true)
<!-- ![sc2](https://github.com/lbormann/autodarts-wled/blob/main/showcase/2.jpg?raw=true)
![sc3](https://github.com/lbormann/autodarts-wled/blob/main/showcase/3.jpg?raw=true)
![sc4](https://github.com/lbormann/autodarts-wled/blob/main/showcase/4.jpg?raw=true)
![sc5](https://github.com/lbormann/autodarts-wled/blob/main/showcase/5.jpg?raw=true) -->


## Best working and looking LED-Location

To find the best possible light-impression without causing problem to dart-recognition algorithmn, I tried different led-stripe positions: 
1. As main lighting (in a plasma lighting ring): It`s way too dark - ugly as my softring is black (It should be definitely better with a white one).
2. Around the plasma lighting ring (outside): Not really a light-effect at all, as light has nothing to shine at.
3. Around my softring: Works best and looks nice! But you need a bright background/wall.

I`ve tested 1.) with a white soft ring. It looks OK, but the recognition algorithmn can NOT handle this: When a led-effect is played it does not recognize pulling.. after pressing next to end the turn, the recognition stops completely and you need to restart your board.

Moreover as a general impression: If the leds are too far away from wall the effect is not good. More far away = more bad - just ez like that.
In my experience the primary factor causing false-positive recognitions is an excessive high led-brightness; you should limit your leds to a certain power draw (ex. 2500 mA).

Here is my currrent Hardware-Setup (You can google prices yourself):
* Controller: 1x AZDelivery ESP32 D1 Mini
* Led-stripe: 1x BTF-Lighting SK6812 RGBNW 60leds/m - ~ 4.4m used
* Power adapter: 1x Mean Well LPV-100-5 60W 5V DC
* Cosmetic: 1x fowong 2m Selbstklebend Dichtungsband 12mm(B) x 12mm(D) x 4m(L) Schaumstoffband (to prevent visible leds)
* Connector: 4x Wago 221-612 Verbindungsklemme 2 Leiter mit Betätigungshebel 0,5-6 qmm (to easily connect cables)
* Connector: 2x 3 Pin LED Anschluss 10 mm Lötfreier LED Licht Anschluss (to easily connect led-stripe segments)



## INSTALL INSTRUCTION

### Windows

- Download the executable in the release section.


### Linux / Others

#### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip.


#### Get the project

    git clone https://github.com/lbormann/autodarts-wled.git

Go to download-directory and type:

    pip install -r requirements.txt



## RUN IT

### Prerequisite

You need to have a running caller - https://github.com/lbormann/autodarts-caller - (latest version) with configured 'WTT'-Argument (http://127.0.0.1:8081)

### Run by executable (Windows)

Create a shortcut of the executable; right click on the shortcut -> select properties -> add arguments in the target input at the end of the text field.

Example: C:\Downloads\autodarts-wled.exe -WEPS "your-first-wled-url" "your-second-wled-url"

Save changes.
Click on the shortcut to start the application.


### Run by source

    python3 autodarts-wled.py -WEPS "your-wled-url"



### Setup autoboot [linux] (optional)

    crontab -e

At the end of the file add:

    @reboot sleep 30 && cd <absolute-path-to>/autodarts-wled && python3 autodarts-wled.py -WEPS "your-wled-url"

Make sure you add an empty line under the added command.

Save and close the file. 

Reboot your system.


### Arguments

- -I / --host_ip [OPTIONAL] [Default: "0.0.0.0"] 
- -P / --host_port [OPTIONAL] [Default: "8081"] 
- -WEPS / --wled_endpoints [REQUIRED] [MULTIPLE ENTRIES POSSIBLE] 
- -BRI / --effect_brightness [OPTIONAL] [Default: 175] [Possible values: 1 .. 255] 
- -DU / --effect_duration [OPTIONAL] [Default: 0] [Possible values: 0 .. 10] 
- -HFO / --high_finish_on [OPTIONAL] [Default: None] [Possible values: 2 .. 170] 
- -HF / --high_finish_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -IDE / --idle_effect [OPTIONAL] [Default: "solid|black"] [Possible values: See below] 
- -G / --game_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -M / --match_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -B / --busted_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -S{0-180} / --score_{0-180}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 
- -A{1-12} / --score_area_{1-12}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: See below] 



#### **-I / --host_ip**

This is your network adress whereat autodarts-caller or other compatible services can send event-data to trigger your wled(s). By Default this is 0.0.0.0 (means your local ip-address / usually you do not need to change this)
    
#### **-P / --host_port**

By analogy with -I there is a port which belongs to the address. By Default this is 8081 (usually you do not need to change this)

#### **-WEPS / --wled_endpoints**

Url to your WLED-Website. You can define multiple urls.

#### **-BRI / --effect_brightness**

Brightness for WLED-effects. You can choose a value between 1 and 255. By default this is 175.

#### **-DU / --effect_duration**

Time, in seconds, after a triggered effect/preset/playlist will return to idle-effect. By default this is 0 (infinity duration = return to idle happens when you pull your darts)

#### **-HFO / --high_finish_on**

Define what a highfinish means for you. Choose a score-value between 2 and 170. This value is relevant for argument '-HF'. By default this is not set = no effects for 'Highfinishes'.

#### **-HF / --high_finish_effects**

Controls your wled(s) when a high-finish occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

#### **-IDE / --idle_effect**

Controls your wled(s) when dart-pulling occured (Waiting for dart-throw). You can disable leds by defining an effect 'solid|black' which is the default value.
Define an effect/preset/playlist that gets triggered after dart-pulling. For examples see below!

#### **-G / --game_won_effects**

Controls your wled(s) when a game won occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

#### **-M / --match_won_effects**

Controls your wled(s) when a match won occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

#### **-B / --busted_effects**

Controls your wled(s) when a bust occurs.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

#### **-S{0-180} / --score_{0-180}_effects**

Controls your wled(s) when a specific score occurs. You can define every score-value between 0 and 180.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!

#### **-A{1-12} / --score_area_{1-12}_effects**

Besides the definition of single score-values you can define up to 12 score-areas.
Define one effect/preset/playlist or a list. If you define a list, the program will randomly choose at runtime. For examples see below!


_ _ _ _ _ _ _ _ _ _


#### Examples: 

| Argument | [condition] | effect 1 | effect 2 | effect 3 | effect x |
| --  | -- | -- | --  | -- | -- | 
|-B |  | solid\\|red1 | solid\\|blue2 | | | |
|-A1 | 0-15 | 1\\|s255\\|i255\\|green1\\|red2 | solid\\|red1 | breathe\\|yellow1\\|blue2\\|s170\\|i40 | | |
|-A2 | 16-60 | ps\\|3 | | | 

The first argument-definition shows the event 'Busted': Busting will result in playing one of the 2 defined effects: solid (red) and solid (blue).

The second argument-definition shows a defined 'Score-area': recognized scores between 0 and 15 will result in playing one of the 3 effects: blink (ID: 1), breathe or solid. For every of those effects we defined different colors, speeds and intensities; only the effect-name/effect-ID is required; everything else is an option.


* To set a preset or playlists, use the displayed ID in WLED! 

    syntax: **"ps|{ID}"**

* To set an effect, use an wled-effect-name or the corresponding ID (https://github.com/Aircoookie/WLED/wiki/List-of-effects-and-palettes):

    syntax: **"{'effect-name' or 'effect-ID'}|{primary-color-name}|{secondary-color-name}|{tertiary-color-name}]"**

* To set effect- speed, intensity, palette

    syntax: **"{'effect-name' or 'effect-ID'}|s{1-255}|i{1-255}|p{palette-ID}]"**

* For color-name usage, validate that the color-name you want is available in the list!

    validate at: **https://www.webucator.com/article/python-color-constants-module/**

* To set an random effect, use 'x' or 'X' as effect-id

    syntax: **"x"**

* If you have problems do not hesitate to have a look at example file!

    learn at: **win-exec.bat**




## Community-Effect-Profiles

| Argument | Tullaris#4778 |
| --  | -- | 
| HF (Highfinish) | fire flicker |
| IDE (Idle) | solid\\|lightgoldenrodyellow |
| G (Game-won) | colorloop |
| M (Match-won) | running\\|orange\\|red1 |
| B (Busted) | fire 2012 |
| S0 (score 0) | breathe\\|orange\\|red1 |
| S3 (Score 3) | running |
| S26 (Score 26) | dynamic |
| S180 (Score 180) | rainbow |
| A1 (Area 1) | 0-14 solid\\|deeppink1 |
| A2 (Area 2) | 15-29 solid\\|blue |
| A3 (Area 3) | 30-44 solid\\|deepskyblue1 |
| A4 (Area 4) | 45-59 solid\\|green |
| A5 (Area 5) | 60-74 solid\\|chartreuse1 |
| A6 (Area 6) | 75-89 solid\\|brick |
| A7 (Area 7) | 90-104 solid\\|tomato1 |
| A8 (Area 8) | 105-119 solid\\|tan1 |
| A9 (Area 9) | 120-134 solid\\|yellow1 |
| A10 (Area 10) | 135-149 solid\\|purple1 |
| A11 (Area 11) | 150-164 solid\\|orange |
| A12 (Area 12) | 165-180 solid\\|red1 |


## !!! IMPORTANT !!!

This application requires a running instance of autodarts-caller https://github.com/lbormann/autodarts-caller
Moreover you need to configure the WTT-argument in autodarts-caller to delegate incoming game-events to this application.
Let`s say you drive both - the caller and wled on the same machine, then you fill WTT with 'http://127.0.0.1:8081' Do not use 'localhost' as the name needs to be resolved by os that can cost addional time until the game-event reaches wled.



## HELPERS

If you think it is terrible to configure/start/handling this application then go for autodarts-desktop https://github.com/Semtexmagix/autodarts-desktop


## BUGS

It may be buggy. I've just coded it for fast fun with https://autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs

- add quality photos of a setup example
- error receiving effect-list if WEPS is given with ending '/'
- receive effect-list from all configured endpoints
- turn off wled on match-finish
- add game-mode variable to arguments
- care about powerstate of WLED; cause crash on start possible now
- effect-IDs > 117 have probs (ex 118)

### Done

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



## LAST WORDS

Make sure your wled(s) are working ;)
Thanks to Timo for awesome https://autodarts.io. It will be huge!


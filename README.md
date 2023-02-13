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
| Cricket | o |
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

Here is my currrent Hardware-Setup (You can google prices yourself):
* Controller: 1x AZDelivery ESP32 D1 Mini
* Led-stripe: 1x BTF-Lighting SK6812 RGBNW 60leds/m - ~ 4.4m used
* Power adapter: 1x Mean Well LPV-100-5 60W 5V DC
* Cosmetic: 1x fowong 2m Selbstklebend Dichtungsband 12mm(B) x 12mm(D) x 4m(L) Schaumstoffband (to prevent visible leds)
* Connector: 4x Wago 221-612 Verbindungsklemme 2 Leiter mit Betätigungshebel 0,5-6 qmm (to easily connect cables)
* Connector: 2x 3 Pin LED Anschluss 10 mm Lötfreier LED Licht Anschluss (to easily connect led-stripe segments)


## WLED-Effects

In WLED you can choose between a pre-installed list of effects. You can find a list of possible effects here:
https://github.com/Aircoookie/WLED/wiki/List-of-effects-and-palettes
Notice the 'EffectID' in the first column: this ID is your friend if you want to map an autodart-event to a wled-effect.
Every autodart-event can be mapped to multiple WLED-Effects. An effect will be randomly determined at runtime.
In my experience the primary factor causing false-positive recognitions is an excessive configured led-brightness; you should limit your leds to a certain power draw (ex. 2500 mA).

My favorite effects (WIP): (Please feel free to shout out your favorites on Discord ;)

| Autodart-Event | WLED-Effect-ID |
| ------------- | ------------- |
| Game-Won (-G) | 4 |
| Match-Won (-M) | 4, 87 |
| Busted (-B) | 0 |
| Score-140 (-S140) | 81 |
| Score-180 (-S180) | 78, 9 |



## INSTALL INSTRUCTION

### Windows

- Download the executable in the release section.


### Linux / Others

#### Setup python3

- Download and install python 3.x.x for your specific os.
- Download and install pip


#### Get the project

    git clone https://github.com/lbormann/autodarts-wled.git

Go to download-directory and type:

    pip install -r requirements.txt



## RUN IT

### Run by executable (Windows)

Create a shortcut of the executable; right click on the shortcut -> select properties -> add arguments in the target input at the end of the text field.

Example: C:\Downloads\autodarts-wled.exe -WEPS "your-first-wled-url" "your-second-wled-url"

Save changes.
Click on the shortcut to start the application.


### Run by source

    python autodarts-wled.py -WEPS "your-wled-url"



### Setup autoboot [linux] (optional)

    crontab -e

At the end of the file add:

    @reboot sleep 30 && cd <absolute-path-to>/autodarts-wled && python autodarts-wled.py -WEPS "your-wled-url"

Make sure you add an empty line under the added command.

Save and close the file. 

Reboot your system.


### Arguments

- -I / --host_ip [OPTIONAL] [Default: "0.0.0.0"] ex: "192.168.0.20"
- -P / --host_port [OPTIONAL] [Default: "8081"] ex: "9090"
- -WEPS / --wled_endpoints [REQUIRED] [MULTIPLE ENTRIES POSSIBLE] ex: "http://192.168.0.200"
- -BRI / --effect_brightness [OPTIONAL] [Default: 175] [Possible values: 1 .. 255] ex: "150"
- -HFO / --high_finish_on [OPTIONAL] [Default: None] [Possible values: 2 .. 170] ex: "51"
- -HF / --high_finish_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "13" "14" "15"
- -IDE / --idle_effect [OPTIONAL] [Default: "solid|black"] ex: "solid|lightgoldenrodyellow"
- -G / --game_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "x"
- -M / --match_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "4" "5" "6"
- -B / --busted_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "ps|5" "ps|4"
- -S0 / --score_0_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "100" "101" "102"
- -S180 / --score_180_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "ps|1"
- -S{0-180} / --score_{0-180}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "x"
- -A1 / --score_area_1_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "1-15" "solid|green1" "solid|yellow1" "solid"
- -A2 / --score_area_2_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "141-179" "rainbow" "theater|aliceblue" "beach"
- -A{1-12} / --score_area_{1-12}_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] ex: "x"



* To set a preset or playlists, use the displayed ID in WLED! 

    usage: "ps|{ID}"

* To set an effect, use an wled-effect-name or the corresponding ID (https://github.com/Aircoookie/WLED/wiki/List-of-effects-and-palettes):

    usage: "solid|red1" or "0|yellow1|orange|peachpuff2"

* For color-name usage, validate at https://www.webucator.com/article/python-color-constants-module/ that the color-name you want is available in the list. 

* To set an random effect, use 'x' or 'X' as effect-id

    usage: "x"

* If you have problems do not hesitate to have a look at "win-exec.bat" file as an example!



## HELPERS

If you think it is terrible to configure/start/handling this application then go for autodarts-desktop https://github.com/Semtexmagix/autodarts-desktop


## BUGS

It may be buggy. I've just coded it for fast fun with https://autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs
- add quality photos of a setup example
- error receiving effect-list if WEPS is given with ending '/'
- turn off wled on match-finish


### Done
- create receiver-endpoint
- support events with multiple effects that chosen randomly
- send events to wled-instance(s)
- Random Effect if user enters 'x' as argument value for effect-id
- add high-finish logic
- initial check is wled reachable download effect-names. (maybe turn on wled-installation(s) for 10 Seconds)
- let user choose between effect-index and effect-name in arguments
- support customizung effect-parameters (brightness, bg, speed, width etc.)
- support point-areas
- brightness configurable
- default effect when idle
- try to fix change-too-slow problem (WLED)
- support presets + playlists



## LAST WORDS

Make sure your wled(s) are working ;)
Thanks to Timo for awesome https://autodarts.io. It will be huge!


# AUTODARTS-WLED

Autodarts-wled controls your wled-installation(s) https://github.com/Aircoookie/WLED accordingly to the state of an https://autodarts.io game. A running instance of https://github.com/lbormann/autodarts-caller is needed that sends the thrown points from https://autodarts.io to this application.

Tested on Windows 10 & 11 Pro x64, Python 3.9.7, 
WLED-Installation 0.14.0-b1 (LED-Stripe SK6812 RGBNW 60leds/m - 4,4 meters powered by a 60W power adapter running on an ESP32 D1 Mini)


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
In my experience the primary factor causing false-positive recognitions in autodarts is a configured led-brightness. You should limit your leds to a certain power draw.

My favorite effects (WIP): (Please feel free to shout out your favorites on Discord ;)

| Autodart-Event | WLED-Effect-ID |
| ------------- | ------------- |
| Game-Won (-G) | 4 |
| Match-Won (-M) | 4, 87 |
| Busted (-B) | 0 |
| Score-140 (-S140) | 81 |
| Score-180 (-S180) | 78, 9 |


| WLED-Effect-Name | FX | BG | Speed | Width | Duty Cycle |
| ------------- | ------------- | ------------- | ----------| ------------- | ------------- |
| Solid | red | D | D | D | D |
| Android | D | D | D | D | D |
| Blends | D | D | D | D | D |
| Blink | red | D | 230 | D | D |
| Blink Rainbow | D | D | 230 | D | D |
| Bpm | red | D | 230 | D | D |
| Rainbow | D | D | D | D | D |



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

- -WEPS / --wled_endpoints [REQUIRED] [MULTIPLE ENTRIES POSSIBLE] ex: "http://192.168.0.200"
- -HSO / --high_score_on [OPTIONAL] [Default: None] [Possible values: 1 .. 180] ex: "101"
- -HFO / --high_finish_on [OPTIONAL] [Default: None] [Possible values: 1 .. 170] ex: "51"
- -HS / --high_score_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 0 .. 117 | x] ex: "10" "11" "12"
- -HF / --high_finish_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "13" "14" "15"
- -G / --game_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "x"
- -M / --match_won_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "4" "5" "6"
- -B / --busted_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "7" "8" "9"
- -S0 / --score_0_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "100" "101" "102"
- -S180 / --score_180_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "106" "107" "108"
- -S{0-180} / --score_X_effects [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117 | x] ex: "x"

x = Random effect everytime

For entering colors, use the following link and validate that the color-name you want is available in the list:
https://www.webucator.com/article/python-color-constants-module/

For entering effects, use an wled-effect-name or the corresponding number to this effect:
https://github.com/Aircoookie/WLED/wiki/List-of-effects-and-palettes

If you have problems do not hesitate to have a look at "win-exec.bat" file!



## HELPERS (COMING SOON WIP)

If you think it is terrible to configure/start/handling this application then go for autodarts-desktop https://github.com/Semtexmagix/autodarts-desktop


## BUGS

It may be buggy. I've just coded it for fast fun with https://autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs
- support customizung effect-parameters (brightness, bg, speed, width etc.)
- try to fix change-too-slow problem (WLED)
- support presets
- add quality photos of a setup example


### Done
- create receiver-endpoint
- support events with multiple effects that chosen randomly
- send events to wled-instance(s)
- Random Effect if user enters 'x' as argument value for effect-id
- add high-finish logic
- initial check is wled reachable download effect-names. (maybe turn on wled-installation(s) for 10 Seconds)
- let user choose between effect-index and effect-name in arguments


## LAST WORDS

Make sure your wled(s) are working ;)
Thanks to Timo for awesome https://autodarts.io. It will be huge!


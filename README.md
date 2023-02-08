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


## Best working and looking LED-Location

To find the best possible light-impression without causing problem to dart-recognition algorithmn, I tried different led-stripe positions: 
1. As main lighting (in a plasma lighting ring): It`s way too dark - ugly as my softing is dark (Definitly better with a white softring).
2. Around the plasma lighting ring (outside): Not really a light-effect at all, as light has nothing to shine at.
3. Around my softring: Works best and looks nice! But you need a bright background/wall.



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

- -WEPS / --wled_endpoints [REQUIRED] [MULTIPLE ENTRIES POSSIBLE] ex: "http://wled-dart.local"
- -HSO / --high_score_on [OPTIONAL] [Default: None] [Possible values: 1 .. 180] ex: "101"
- -HFO / --high_finish_on [OPTIONAL] [Default: None] [Possible values: 1 .. 170] ex: "51"
- -G / --game_won_effect_ids [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "1" "2" "3"
- -M / --match_won_effect_ids [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "4" "5" "6"
- -B / --busted_effect_ids [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "7" "8" "9"
- -HS / --high_score_effect_ids [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "10" "11" "12"
- -HF / --high_finish_effect_ids [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "13" "14" "15"
- -S0 / --score_0 [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "100" "101" "102"
- -S60 / --score_60 [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "103" "104" "105"
- -S100 / --score_100 [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "103" "104" "105"
- -S140 / --score_140 [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "103" "104" "105"
- -S180 / --score_180 [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "106" "107" "108"
- -S{X} / --score_X [OPTIONAL] [MULTIPLE ENTRIES POSSIBLE] [Default: None] [Possible values: 1 .. 117] ex: "106" "107" "108"

X = every value between 0 and 180!


## EXTENSIONS (COMING SOON WIP)

If you think it is terrible to configure/start/handling this application then go for autodarts-desktop https://github.com/Semtexmagix/autodarts-desktop


## BUGS

It may be buggy. I've just coded it for fast fun with https://autodarts.io. You can give me feedback in Discord > wusaaa


## TODOs
- initial check is wled reachable download effect-names. (maybe turn on wled-installation(s) for 10 Seconds)
- let user choose between effect-index and effect-name in arguments
- support arg for customizing common brightness
- support customizung effect-parameters (ie bg, speed)
- support presets
- add quality photos of a setup example
- fix game-start leds off is too late: recog is confused.


### Done
- create receiver-endpoint
- support events with multiple effects that chosen randomly
- send events to wled-instance(s)


## LAST WORDS

Make sure your wled(s) are working ;)
Thanks to Timo for awesome https://autodarts.io. It will be huge!


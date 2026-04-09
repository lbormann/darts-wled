PUSHD .
python "darts-wled.py" ^
-CON "127.0.0.1:8079" ^
-WEPS "your-primary-wled-ip" "your-secondary-wled-ip" ^
-DU "0" ^
-BSS "0.0" ^
-BRI "255" ^
-HFO "51" ^
-HF "x" ^
-IDE "solid|lightgoldenrodyellow" ^
-G "4" "87" "26" "29" "93" "42" "64" ^
-M "4" "87" "26" "29" "93" "42" "64" ^
-B "solid|red1" "1|red1" "ps|3|5" ^
-PJ "solid|green1" ^
-PL "solid|red1" ^
-S26 "84" ^
-S45 "Phased" ^
-S41 "Phased" ^
-S60 "13" ^
-S80 "29|blueviolet|yellow|yellow1" "rainbow|blue|yellow|yellow1" "13|aliceblue|yellow|yellow1" ^
-S100 "27" ^
-S120 "8" ^
-S140 "ps|3" ^
-S180 "78" "9" ^
-A1 "1-60" "ps|2" "solid|yellow1" ^
-A2 "16-30" "blink|green1" "rainbow|yellow1" "blink|peachpuff2" ^
-A3 "61-120" "29|blueviolet|s125|i145|red1|green1|p4"^
-BSW "1" 
-BSE "solid|red1" ^
-TE "solid|lightgoldenrodyellow" ^
-CE "solid|blue" ^
-OFF "0"

REM Multi-WLED targeting examples for -WEPS order: 0=primary, 1=secondary, 2=third device
REM Example endpoints:
REM -WEPS "192.168.1.100" "192.168.1.101" "192.168.1.102"
REM
REM Idle only on device 1, score animations on device 0, status on devices 1 and 2:
REM -IDE "solid|lightgoldenrodyellow|e:1" ^
REM -S26 "dynamic|e:0" ^
REM -S180 "fire|e:0" "solid|gold1|e:1,2" ^
REM -B "solid|red1|e:0,1,2" ^
REM -G "ps|9|e:0" "ps|11|e:1,2|10" ^
REM -M "running|orange|red1|e:0" "solid|blue|e:1,2" ^
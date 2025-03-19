# forza-pi-dash
This project is a small sim dashboard for Forza Motorsport using the game's 'data out' feature. It is built to run on a Raspberry Pi running PiOS with a small 800x480 display (but also works on a desktop). The idea is to run this dashboard on the pi and attach it to a wheelbase/sim rig/desk for extra immersion.

![Screenshot (21)](https://github.com/user-attachments/assets/033c0c09-a6fa-4927-befd-e24e4216ec29)

## How it works
Forza sends a stream of UDP packets roughly 60 times a second to a specified ip address and port that the player sets in game. Each UDP packet contains information about the player and their car at that current point in time. For example the current lap number, the player's race position, tire temperatures, and various other points of data. This dashboard reads each packet, organises the data, formats it and displays it in a race-like live dashboard.

## Features

### Time Delta
The dash incorporates a live time delta widget updated each time a packet is received, up to 60 times a second. It compares your currant lap time to your best lap time in the session. It does not matter if the best lap was a forza-clean lap, and remembers your lap time even when you pause the game - something that (strangely) a lot of the sim hub dashboards don't do.

This feature currently **doesn't work during timed races** and will report an inconsistent time. This is due to a bug in forza's data out feature where during timed races, it uses the currant lap time parameter to report currant distance. This is a ridiculous bug and makes it impossible for any dashboard to track currant lap time. Hopefully they will fix it soon.

### Customisable Tire Temp and Wear
Tire wear and temperature for each tire is shown in the bottom left. Tire wear is shown as a percentage (higher means more tire wear), and temperature is shown visually using colours. A *Green* tire means it is currently within it's optimum tire temp window. *Blue* is too cool, *yellow* is getting too hot but still usable, and *red* is too high. These colour warnings can be customised in the settings window. (See **Settings**)

### Position, Lap, Distance, and Time
Your currant position, lap number and total race distance is shown in the top left. Your last lap time, best lap time and currant lap time are shown in the top right. Just like the time delta feature, **currant lap won't work during timed races due to the same reason.**

### Fuel Monitoring
Currant fuel level is shown as a number between 0 and 1. 0 Means no fuel left, 1 means a full tank. Fuel per lap and laps left are an estimated figure based on the amount of fuel used on the last 3 laps, and is updated each lap. When the estimated laps left falls below 1, a warning is shown advising to pit this lap.

### Customisable Shift Light
The gear indicator will turn yellow when it's nearly time to shift up, and will turn red when the car is near it's maximum rpm. You can control when they indicator will change colour in the settings. (See **Settings**)

### Tire Slip Indicators
Tire slip indicators for the rear left and rear right tires are shown on either side of the dash. The higher the bar, the more slip, the less grip.

## Download and Installation
1. Make sure the latest version of Python is installed.
2. Create a Python virtual environment and activate it
- `python3 -m venv venv_name`
- `source venv_name/bin/activate` (linux)
- `venv_name\Scripts\activate.bat` (windows)
3. Clone this project
4. Install the required Python packages (located in requirements.txt) into the virtual environment
- `pip install -r requirements.txt`

## Running the Dashboard
The main file to run is called `forza-pi.py` and is located in the 'src' directory. Run `python src/forza-pi.py` to start the dashboard. It will launch in a new window, and start logging to the terminal.

Enable Data Out in Forza by navigating to Settings > Gameplay & Hud > UDP Race Telemetry, and switch the Data Out setting to On.

Match the Data Out IP Address setting in Forza to the IP address of the raspberry pi (or the computer running the dashboard). To find this, go to the *Settings* tab in the dashboard. It should be displayed at the top and look something like '192.168.7.54'.

Match the Data Out IP Port setting in Forza to the Port number in the dashboard. This is located in the *Settings* tab in the dashboard. By default it should be 1337, but you can change this.

Exit out of the dashboard settings (click save or cancel) and hit Start. The dashboard will start listening for data sent by Forza, and the buttons at the top will be dimmed to avoid distraction. If it isn't working it could be one of a few things:

- The dashboard isn't on the same network as Forza - make sure they are both running on your home network, and disable any VPNs
- The port or IP address doesn't match
- The dashboard is displaying the wrong IP address. In the raspberry pi, open the terminal and type `ifconfig`. The address you want should be displayed. If in doubt, Google it.
- Forza isn't sending any data. If the red 'Not Racing' alert is displayed, it means Forza isn't sending any data.

Once it's all working and displaying data, you can stop it by hitting the 'Stop' button. If you want to start a new session, you can **reset the dashboard** by hitting the 'Reset' button. This will clear all the widgets including the interval and fuel displays so they don't continue to use data from a previous session.

## Settings and Configuration
You can customise the dashboard in the settings tab by editing the following:
- **Port**: Change this number to change which port the dashboard will listen to. This should match the Data Out IP Port setting in Forza
- **Speed Units**: Can either be *metric* or *imperial* to display the speed in kmh or mph respectively
- **Distance Units**: Can either be *metric* or *imperial* to display the distance in kilometers or miles respectively
- **Redline Percent**: When the current RPM reaches this percentage of the engine's max RPM, the gear indicator will turn red. The higher this number, the more RPMs it will take
- **Ready Percent**: Similar to above, but will turn the indicator yellow instead. This number should be below the redline percent
- **Blue Tire Temp**: When a tire reaches or goes below this temperature, it will turn blue to indicate cool tires. Currently this temperature is *Fahrenheit only*
- **Yellow Tire Temp**: When a tire reaches or goes above this temperature, it will turn yellow to indicate warm tires. Currently this temperature is *Fahrenheit only*
- **Red Tire Temp**: When a tire reaches or goes above this temperature, it will turn red to indicate hot tires. Currently this temperature is *Fahrenheit only*

## Limitations
- As the dashboard is designed for a specific resolution (800 x 480), it doesn't resize very well. If you really want to resize it, you can edit the style.qss file, or the default size of the dashboard found in Dashboard's init method.
- As explained above, the currant lap time and interval widgets won't work for timed races and will stay this way until Turn 10 start making good life decisions
- Currently no UDP forwaring, so this should be the last device in a UDP-chain
- There might be some bugs here and there as it's just a small project and not intended for any kind of commercial release, but I will update it here and there when I feel like it

## Future Features
- More Alerts and Warnings (Eg. larger fuel warning, tire temp warnings)
- More interactive widgets (Click a widget to change its units)
- Programmable strategy (Eg. pit warning after 7 laps/ 30 minutes)
- Less spaghettified settings code for better maintaining
- UDP forwarding
- File saving
- Exporting session data
- Telemetry tab to view session data and traces
- 3D printed/Laser cut case and stand for the Raspberry Pi to attach it to wheels/desks etc

If you would like to develop this further, feel free to fork this repository and start working on your own features! Just make sure to include the proper licenses in your project :)

## Hardware Used to Build the Dashboard
- Raspberry Pi 4 4gb running PiOS
- Waveshare 4.3" DSI QLED Touchscreen Display for Raspberry Pi (https://www.waveshare.com/wiki/4.3inch_DSI_QLED) (Very easy to install, just connect the display cable to the Pi - no drivers or editing config files)
- Waveshare Low-Profile CPU Cooling Fan (https://www.waveshare.com/wiki/PI-FAN-3007) (Not really necessary unless you live in a very hot climate. With the fan running the CPU temps were around 30C)
- 4 M2.5 x 8mm screws to attach the display, Pi and fan together

![1000009019(1)](https://github.com/user-attachments/assets/46adc3e2-bb20-4c6b-8e6f-db48db7de8dd)
![1000009018(1)](https://github.com/user-attachments/assets/ffd8681c-412c-4f83-ae37-da5ed2f69bc4)


# forza-pi-dash
This project is a small motorsport dashboard for Forza Motorsport using the game's 'data out' feature. It is built to run on a raspberry pi running PiOS with a small 800x480 display (but also works on a desktop). The idea is to run this dashboard on the pi and attach it to a wheelbase for extra immersion. It also displays the same data independent of the HUD meaning, for example, you can see distance on the pi when you can't in the game.

## How it works
Forza sends a stream of UDP packets roughly 60 times a second to a specified ip address and port that the player sets in game. Each UDP packet contains information about the player and their car at that current point in time. For example the current lap number, the player's race position, tire temperatures, and various other points of data. This dashboard reads each packet, organises the data, formats it and displays it in a race-like live dashboard.

## Features
- A live, very-accurate time delta
- Live tire temperature and tire wear
- Live fuel monitoring and lap predictions
- Distance, position, last and best lap displays
- 4 customisable widgets to display direct forza parameters
- Configurable settings

## Limitations
This is a very early v1 prototype of a dashboard that was built very quickly as a proof of concept and with very limited knowledge of the Qt GUI framework. It has many bugs, it has not been extensively tested, and is a mess of spaghetti code. But it's got charm. It does what it says on the tin. Sort of.

## Download and Installation
    1. Make sure the latest version of Python is installed.
    2. Create a Python virtual environment and activate it
        - python3 -m venv venv_name
        - source venv_name/bin/activate (linux)
        - venv_name\Scripts\activate.bat (windows)
    3. Clone this project
    4. Install the required Python packages (located in requirements.txt) into the virtual environment
        - pip install -r requirements.txt

## Running the Dashboard
    1. Set the 'Data Out IP Address' setting in Forza to the ip address of your computer. To find your ip address either:
        1. For linux, run the ifconfig command in the terminal and write down the ip address next to 'inet'
        2. For windows, run the ipconfig command in the terminal and write down the ipv4 address
        It may look something like '192.168.7.43'. If in doubt, google is your friend.
    2. Set the 'Data Out IP Port' setting in Forza to 1337 (If you want to change this, make sure to also change the 'port' setting in the dashboardConfig.yaml file)
    3. In the terminal (with your virtual environment activated) run 'python forza-pi.py'
    4. Press the 'Start' button to start listening for packets, press again to pause the dashboard
        

## Configuration
The project uses a few configuration files to function and to customise the dashboard to the player's liking. They are yaml files so they are easy to read and edit. Eventually, they will be completely replaced by a settings window inside the dashboard.

### dashboardConfig.yaml
This is the main configuration file and holds all the user preferences and dashboard configurations. It is already pre-configured with some generic values:
- **port**: The port that the dashboard will listen on. This should match the 'Data Out IP Port' setting found in the 'Gameplay & HUD' tab in Forza
- **unitOptions**: Some options for the type of units each parameter can take
- **units**: The current chosen units that each parameter will take. Must match one of the choices found in *unitOptions*
- **redlinePercent**: When the current RPM reaches this percentage of the engine's max RPM, the gear indicator will turn red
- **readyPercent**: When the current RPM reaches this percentage of the engine's max RPM, the gear indicator will turn yellow. Should be less than *redlinePercent*
- **tireTempBlue**: When a tire reaches or goes below this temperature, it will turn blue
- **tireTempYellow**: When a tire reaches or goes beyond this temperature, it will turn yellow
- **tireTempRed**: When a tire reaches or goes beyond this temperature, it will turn red
- **pitWarning**: Controls the pit warning widget contained in the fuel tab. Set to **True** to activate. Set to **False** to deactivate.
- **parameterList**: A list of 0 to 4 Forza data parameters that the dashboard will display as small widgets underneath the gear indicator. These parameters should match the parameters found in *paramConfig.yaml*. By default, these are speed, current_engine_rpm, power, and boost

### paramConfig.yaml
This file stores all the parameters that Forza sends as part of a single packet. It also stores a user-friendly label for that parameter, the possible units that parameter can be, a conversion factor for each unit, and a sensible number of decimal places for ths parameter. Don't edit this file unless you really want to define your own custom unit configuration.

## Troubleshooting
If this doesn't run, it is likely due to the following:
- Wrong IP Address: try another IP address and run the dashboard again
- Packages haven't installed correctly: Check all the packages have been installed by running 'pip list'. The versions I have listed in requirements.txt might not be available yet, so try a previous version. Or, install them manually. You only need to install PySide6 (it will install its dependencies automatically) and PyYaml.
- Port is unavailable: Try changing the port number in dashboardConfig.yaml. Remember to also change it in Forza
- It just doesn't run: I have developed this on Ubuntu so it might just not work on your system :(
Version 1 is a very janky prototype so it might just not run currently. If you're handy with Python, it might be worth trying different packages, or simply debugging this project in VS Code.

## Planned Features
- Settings tab to replace config files
- A more cohesive and responsive interface
- More specific widgets displaying current units
- Alerts and Warnings (Eg. larger fuel warning, tire temp warnings)
- More interactive widgets (Click a widget to change its units)
- Programmable strategy (Eg. pit after 7 laps/ 30 minutes)
- UDP forwarding
- File saving
- Exporting session data
- Telemetry tab to view traces
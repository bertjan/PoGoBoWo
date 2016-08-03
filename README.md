PoGoWoBo
========
[![Build Status](https://travis-ci.org/BoBeR182/PoGoBoWo.svg?branch=master)](https://travis-ci.org/BoBeR182/PoGoBoWo)

Bitcoin: 1HJ5kY14HMTjE3DfTEDr9YkRMxCS5PHPta

## Disclaimer! 
Niantic may softban you if you run the bot while signed in through your phone.
Softbans will happen if you teleport around the world too much.

Using this bot violates the ToS and can result in a permaban, none have happened yet.

Server status can be found at https://go.jooas.com/

### Features
+ Incubate eggs
+ CLI based to run on VPS
+ Auto evolve
+ Auto transfer
+ Auto catch
+ Auto spin pokestop
+ Auto top up pokeballs
+ Google API for location and realistic walking paths
+ Multi account support (just add more entries in config.json)
+ Includes a basic web UI to monitor your bot

### Instructions
1. Fork/Clone project. `git clone https://github.com/BoBeR182/PoGoBoWo`.
2. Change into the directory `cd PoGoBoWo`.
3. You need to install Python version 2.7 and have pip installed; (I recommend setting up a VirtualEnv)
4. Install the dependencies with: `pip install -r requirements.txt`
5. Create a Google Maps Directions API key and activate it:
    1. Create it here: https://console.developers.google.com/projectselector/apis/credentials
    2. Then activate it here (select your project on the dropdown menu): https://console.developers.google.com/apis/api/directions_backend/overview?project=_
6. Then `cp config.json.example config.json` file.
7. Edit the file with your username, location, password, Google API, and anything else you want to change. (See wiki for documentation)
8. If you login into Pokemon Go with Google: `python pokebot.py -i 0` and `python pokebot.py -i 1` if you use Pokemon Trainer's Club.
9. When running the bot for the first time add `--cache` to the end.
10. ???
11. Profit.

99. You can now open your browser and navigate to `http://localhost:3001` and checkout your bot's progress.
You can change the port by changing the `PORT` env var. eg start your bot with `PORT=8080 python pokebot.py -i 0`.

## Contibuting and TODO

Feel free to contribute code, all you need to do is run `tox` before a commit or check with TravisCI.
`pip install tox`

+ Move as many options from pgoapi.py into config.json to allow user customization.
+ Fix all the issues. https://github.com/BoBeR182/PoGoBoWo/issues
+ We need user freindly documentation in the https://github.com/BoBeR182/PoGoBoWo/wiki.
+ Two modes, as fast XP as possible, or human and undetectable.
+ Auto lucky egg/incense.
+ Detect softban and bypass or avoid softbans.
+ Auto Gym
+ Make it easier to contirbute to.

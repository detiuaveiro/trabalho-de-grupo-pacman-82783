### IA PACMAN
Client-Server PACMAN clone

# Description
A Pacman game build over a client and server modules. The client module receive the game state each 100ms and need to reply with a moviment ('a','w','s','d') each interval. 
To calculate the best movement the Pacman analize the postion of the points, boosters and ghosts in a algorithm and decide the direction to take.

# Install

* Clone this repository
* Create a virtual environment:

```console
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r requirements.txt
```
# How to run:
Open 3 terminals, in each terminal runonce:
```console
$ source venv/bin/activate
```
Run each application in it's terminal:

Terminal 1:
```console
$ python server.py
```
Terminal 2:
```console
$ python viewer.py
```
Terminal 3:
```console
$ python client.py
```

# Credits
Sprites from https://github.com/rm-hull/big-bang/tree/master/examples/pacman/data

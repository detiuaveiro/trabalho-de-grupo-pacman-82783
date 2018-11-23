import sys
import json
import asyncio
import websockets
import os
import time
from mapa import Map

def smaller(l):
    if len(l) == 1:
        return l[0]
    min = smaller(l[1:])
    if min < l[0]:
        return min
    return l[0]

def smaller_index(coast):
    index = 0
    for i in range(len(coast)):
        if coast[i] < coast[index]:
            index = i
    return index

def smaller_cost(pacman, vector, mapa, map_coast = {} ):
    x,y = pacman
    coast = []
    for item in vector:
        custo=1
        if tuple(item) in map_coast:
            custo = map_coast[tuple(item)]
        coast.append(int((abs(x-item[0])**2) + (abs(y-item[1])**2)) * custo)
    return vector[smaller_index(coast)]


def gerate_moves(goal):
    x,y = goal

    if x == 18:
        x_plus= 0
    else:
        x_plus = x+1
    
    if x == 0:
        x_minus= 18
    else:
        x_minus= x-1

    return [[x_plus, y],[x_minus,y], [x, y+1],[x,y-1]]   #by index 0-d, 1-a, 2-w, 3-s

def trace_router(pacman, goal, mapa, map_coast = {}):
    
    moves = gerate_moves(goal)

    if pacman == moves[0] and not mapa.is_wall(moves[0]): 
        return 'a' 
    elif pacman == moves[1] and not mapa.is_wall(moves[1]): 
        return 'd' 
    elif pacman == moves[2] and not mapa.is_wall(moves[2]): 
        return 'w' 
    elif pacman == moves[3] and not mapa.is_wall(moves[3]): 
        return 's'  
    
    cur_map_coast = map_coast
    if tuple(goal) in cur_map_coast:
        cur_map_coast[tuple(goal)]+=1
    else:
        cur_map_coast[tuple(goal)]=2

    return trace_router(pacman, smaller_cost(pacman = pacman, vector = [[x,y] for x,y in moves if not mapa.is_wall((x,y))] ,map_coast = map_coast, mapa = mapa ), mapa = mapa, map_coast = cur_map_coast)


async def agent_loop(server_address = "localhost:8000", agent_name="82783"):
    async with websockets.connect("ws://{}/player".format(server_address)) as websocket:

        # Receive information about static game properties 
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        msg = await websocket.recv()
        game_properties = json.loads(msg) 

        mapa = Map(game_properties['map'])

        #init agent properties 
        key = 'd'
        x,y = 3,15
        goal=[1,14]
        while True: 
            r = await websocket.recv()
            state = json.loads(r) #receive game state
            if len(state) ==1:
                return            
            if not state['lives']:
                print("GAME OVER")
                return

            cur_pos = [x,y]
            x,y = state['pacman']
            if goal not in state['boost'] and state['boost']:
                goal = smaller_cost(state['pacman'], state['boost'], mapa = mapa)
                move_coast = {}
            elif state['boost'] == [] and state['energy']:
                if goal not in state['energy']:
                    goal = smaller_cost(state['pacman'], state['energy'], mapa = mapa)
                    move_coast = {}


            if (x,y) in move_coast:
                move_coast[(x,y)]+=1
            else:
                move_coast[(x,y)]=2
            if cur_pos == [x,y]:
                move_coast[tuple(cur_pos)]+=5

            cur_moves = [[x,y] for x,y in gerate_moves(cur_pos) if not mapa.is_wall((x,y))]
            moves = [[x,y] for x,y in gerate_moves([x,y]) if not mapa.is_wall((x,y))]
          

            if len(cur_moves) < len (moves) or cur_pos == [x,y]:
                key = (trace_router( pacman = (state['pacman']), goal = goal, mapa = mapa, map_coast = move_coast))

            #send new key
            await websocket.send(json.dumps({"cmd": "key", "key": key}))


loop = asyncio.get_event_loop()
SERVER = os.environ.get('SERVER', 'localhost')
PORT = os.environ.get('PORT', '8000')
NAME = os.environ.get('NAME', '82783')
loop.run_until_complete(agent_loop("{}:{}".format(SERVER,PORT), NAME))
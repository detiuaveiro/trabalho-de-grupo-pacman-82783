import random
import sys
import json
import asyncio
import websockets
import os
import time
import argparse
from mapa import Map

def calc_dist(item1, item2):
    if item2==[] or item2 == None:
        return 500
    return int( (abs(item1[0]-item2[0])**2) + (abs(item1[1]-item2[1])**2))

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

def smaller_cost(pacman, vector, map_coast = {}, hunter = False):
    coast_lst = []
    if type(vector[0][1]) == bool:
        vector = [x[0] for x in vector if x[1] == hunter ] 
    for item in vector:
        coast=1
        if tuple(item) in map_coast:
            coast = map_coast[tuple(item)]
        coast_lst.append( calc_dist(pacman,item) * coast)
    if coast_lst == []:
        return None
    return vector[smaller_index(coast_lst)]

def generate_moves(goal):
    x,y = goal
    if x == 18:
        x_plus= 0
    else:
        x_plus = x+1
    if x == 0:
        x_minus= 18
    else:
        x_minus= x-1

    return  [[x_plus, y],[x_minus,y], [x, y+1],[x,y-1]] 

def trace_router(pacman, goal, mapa, map_coast = {}):
    
    moves = generate_moves(goal)
    if pacman == moves[0]: 
        return 'a' 
    elif pacman == moves[1]: 
        return 'd' 
    elif pacman == moves[2]: 
        return 'w' 
    elif pacman == moves[3]: 
        return 's'  
    
    cur_map_coast = map_coast
    if tuple(goal) in cur_map_coast:
        cur_map_coast[tuple(goal)]+=1
    else:
        cur_map_coast[tuple(goal)]=2
    return trace_router(pacman, smaller_cost(pacman = pacman, vector = [[x,y] for x,y in moves if not mapa.is_wall((x,y))] ,map_coast = map_coast), mapa = mapa, map_coast = cur_map_coast)

def high_ghost(moves, ghosts, second_objective, ghost_coast):
    move_coast=[0]*len(moves) 
    pos_ghosts = set([tuple(g[0]) for g in ghosts if not g[1]])
    
    for i in range(len(moves)):
        for g in pos_ghosts:
            move_coast[i]+= 1/(1+calc_dist(moves[i],g))
        move_coast[i] -= 1/(1+calc_dist(moves[i],second_objective)/2)
        coast=1
        if tuple(moves[i]) in ghost_coast:
            coast = ghost_coast[tuple(moves[i])]   
            move_coast[i] = move_coast[i] * coast   

    return moves[smaller_index(move_coast)]

async def agent_loop(server_address = "localhost:8000", agent_name="82783"):
    async with websockets.connect("ws://{}/player".format(server_address)) as websocket:

        # Receive information about static game properties 
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        msg = await websocket.recv()
        game_properties = json.loads(msg) 

        mapa = Map(game_properties['map'])

        #init agent properties 
        x,y = 3,15
        goal=[3,14]
        while True: 
            r = await websocket.recv()
            state = json.loads(r) #receive game state
            if len(state) == 1:
                #print(state['score'])
                return            
            if not state['lives']:
                print("GAME OVER")
                #print(state['score'])
                return
            cur_pos = [x,y]
            x,y = state['pacman']
            runner=False

            if state['ghosts'] and calc_dist(state['pacman'], smaller_cost(state['pacman'], state['ghosts']) ) <= 16:
                moves = [ x for x in generate_moves(state['pacman']) if not mapa.is_wall(x)]

                if calc_dist(state['pacman'], smaller_cost(state['pacman'], state['ghosts'])) < 100:
                    second_objective = smaller_cost(state['pacman'], state['ghosts'], {}, hunter = True)
              
                if state['boost'] and not second_objective and calc_dist(state['pacman'], smaller_cost(state['pacman'], state['boost'])) < 100:
                    second_objective = smaller_cost(state['pacman'], state['boost'])
              
                if state['energy'] and not second_objective:
                    second_objective = smaller_cost(state['pacman'], state['energy'])
                goal=high_ghost(moves, state['ghosts'], second_objective, ghost_coast)
                runner=True

                if (x,y) in ghost_coast:
                    ghost_coast[(x,y)]+=1
                else:
                    ghost_coast[(x,y)]=2


            elif state['ghosts'] and calc_dist(state['pacman'], smaller_cost(state['pacman'], state['ghosts'], {} , hunter = True)) < 160:
                goal=smaller_cost(state['pacman'], state['ghosts'],  hunter = True)
                runner=True
            elif state['energy'] and goal not in state['energy']:
                goal = smaller_cost(state['pacman'], state['energy'])
                move_coast = {}                

            if (x,y) in move_coast:
                move_coast[(x,y)]+=1
            else:
                move_coast[(x,y)]=2
            cur_moves = [[x,y] for x,y in generate_moves(cur_pos) if not mapa.is_wall((x,y))]
            moves = [[x,y] for x,y in generate_moves([x,y]) if not mapa.is_wall((x,y))]
            if runner:
                key = trace_router( pacman = (state['pacman']), goal = goal, mapa = mapa)
            elif len(cur_moves) < len (moves) or cur_pos == [x,y]:
                key = trace_router( pacman = (state['pacman']), goal = goal, mapa = mapa, map_coast = move_coast)
                ghost_coast={}
            #send new key
            await websocket.send(json.dumps({"cmd": "key", "key": key}))


SERVER = os.environ.get('SERVER', 'localhost')
PORT = os.environ.get('PORT', '8000')
NAME = os.environ.get('NAME', '82783')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", help="IP address of the server", default=SERVER)  
    parser.add_argument("--port", help="TCP port", type=int, default=PORT)
    parser.add_argument("--name", help="Name of the client", type=str, default=NAME)
    args = parser.parse_args()
    SERVER = args.server
    PORT = args.port 
    NAME = args.name
    LOOP =asyncio.get_event_loop()

    try:
        LOOP.run_until_complete(agent_loop("{}:{}".format(SERVER,PORT), NAME))
    finally:
        LOOP.stop()

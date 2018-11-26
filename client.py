import random
import sys
import json
import asyncio
import websockets
import os
import time
from mapa import Map

def quick_sort(l):
    if len(l) <= 1:
        return l
    else:
        return quick_sort([e for e in l[1:] if e <= l[0]]) + [l[0]] +\
            quick_sort([e for e in l[1:] if e > l[0]])

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

def high_ghost(moves, ghosts, boost):
    move_coast=[0]*len(moves)
    for i in range(len(moves)):
        for g in ghosts:
            if not g[1]:
                move_coast[i]+= 1/(1 + calc_dist(moves[i],g[0]))
        move_coast[i] -= 1/(1+calc_dist(moves[i],boost))  
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
                return            
            if not state['lives']:
                print("GAME OVER")
                return
            cur_pos = [x,y]
            x,y = state['pacman']
            runner=False
            #ghosts=state['ghosts']
            #for coord, boolean,  [9, 15], false, 0]

#            for pos, boolean, i in state['ghosts']:
#                if calc_dist([x,y],pos) <= 5:
#                   ghost=True

#            print([cont for pos, boolean, cont in state['ghosts'] if boolean])
#            if ghost:
#               goal = 
#                move_coast = {}
#               move_coast = { pos: 10 for pos, boolean, time in state[ghost] if calc_dist(state['pacman'],pos) <= 5 }

            #elif goal not in state['boost'] and state['boost']:
            #    goal = smaller_cost(state['pacman'], state['boost'], mapa = mapa)
            #    move_coast = {}
            #elif state['boost'] == [] and state['energy']:
            if state['ghosts'] and calc_dist(state['pacman'], smaller_cost(state['pacman'], state['ghosts']) ) <= 5:
                moves = [x for x in gerate_moves(state['pacman']) if not mapa.is_wall(x)]
                second_objective =  smaller_cost(state['pacman'], state['ghosts'], {}, hunter = True)
                if state['boost'] and not second_objective:
                    second_objective = smaller_cost(state['pacman'], state['boost'])
                if state['energy'] and not second_objective:
                    second_objective = smaller_cost(state['pacman'], state['energy'])
                goal=high_ghost(moves, state['ghosts'], second_objective)
                runner=True
                move_coast={}

            elif state['ghosts'] and calc_dist(state['pacman'], smaller_cost(state['pacman'], state['ghosts'], {} , hunter = True)) < 400:
                goal=smaller_cost(state['pacman'], state['ghosts'],  hunter = True)
                runner=True
            elif state['energy'] and goal not in state['energy']:
                goal = smaller_cost(state['pacman'], state['energy'])
                move_coast = {}                

            if (x,y) in move_coast:
                move_coast[(x,y)]+=1
            else:
                move_coast[(x,y)]=2

            cur_moves = [[x,y] for x,y in gerate_moves(cur_pos) if not mapa.is_wall((x,y))]
            moves = [[x,y] for x,y in gerate_moves([x,y]) if not mapa.is_wall((x,y))]
            #if state['boost'] and state['ghosts'] and calc_dist(state['pacman'], smaller_cost(state['pacman'], state['boost']) ) == 1 :
            #    if calc_dist(state['pacman'], smaller_cost(state['pacman'], state['ghosts']) ) <= 5 :
            #        goal = smaller_cost(state['pacman'], state['boost'])
            #    else:
            #        goal=random.choice([x for x in gerate_moves(state['pacman']) if mapa.is_wall(x)])
            #    key=trace_router(pacman = (state['pacman']), goal = goal, mapa = mapa)

            if runner:
                key = trace_router( pacman = (state['pacman']), goal = goal, mapa = mapa)
            elif len(cur_moves) < len (moves) or cur_pos == [x,y]:
                key = trace_router( pacman = (state['pacman']), goal = goal, mapa = mapa, map_coast = move_coast)
            #send new key
            await websocket.send(json.dumps({"cmd": "key", "key": key}))

loop = asyncio.get_event_loop()
SERVER = os.environ.get('SERVER', 'localhost')
PORT = os.environ.get('PORT', '8000')
NAME = os.environ.get('NAME', '82783')
loop.run_until_complete(agent_loop("{}:{}".format(SERVER,PORT), NAME))
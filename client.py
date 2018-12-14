import time
import random
import sys
import json
import asyncio
import websockets
import os
import argparse
from mapa import Map

def calc_dist(item1, item2):
    if item2==[] or item2 == None:          #default, if item 2 has no value
        return 5000                         #obs: item one is always the pacman, always valide
    return int( (abs(item1[0]-item2[0])**2) + (abs(item1[1]-item2[1])**2))

def smaller_index(vector):
    index = 0
    for i in range(len(vector)):
        if vector[i] < vector[index]:
            index = i
    return index

def smaller_cost(pacman, vector, map_coast = {}):
    if len(vector) > 80:        #assert max len as 80
        vector=vector[0:80]
    
    if vector == []:
        return 

    coast_lst = [0]*len(vector)

    for i in range(len(vector)):            #assign the coast to every position in the vector
        if tuple(vector[i]) in map_coast:
            coast = map_coast[tuple(vector[i])]
        else:
            coast=1
        coast_lst[i] = calc_dist(pacman,vector[i])*coast

    return vector[smaller_index(coast_lst)]

def generate_moves(base):       #return the 4 move possibilities  
    x,y = base
    if x == (mapa.hor_tiles-1):
        x_plus = 0
    else:
        x_plus = x+1
    if x == 0:
        x_minus= mapa.hor_tiles-1
    else:
        x_minus= x-1
    return  [[x_plus, y],[x_minus,y], [x, y+1],[x,y-1]] 

def define_key(pacman,vector):      #each direction the pacman should move
    if pacman == vector[0]: 
        return 'a' 
    elif pacman == vector[1]: 
        return 'd' 
    elif pacman == vector[2]: 
        return 'w' 
    return 's'

def trace_router( pacman, goal, map_coast = {}, control_rec = 0, get_pos = False, ghosts_range = 101):
    if control_rec >= ghosts_range or control_rec > 100:   
        return                #Its means, I don't need to be worried about the ghosts

    if control_rec == 100 and ghosts_range == 101:  #set goal as the closer position the pacman can move to the goal
        goal=smaller_cost(pacman=goal, vector=[[x,y] for x,y in generate_moves(pacman) if not mapa.is_wall((x,y))])
    
    moves = generate_moves(goal)    
        
    if pacman in moves:
        if not get_pos:
            return define_key(pacman,moves)
        return goal

    new_goal = smaller_cost(pacman=pacman, vector=[[x,y] for x,y in moves if not mapa.is_wall((x,y))], map_coast=map_coast)
    
    if tuple(goal) in map_coast:        #control infinity loops with map coast
        map_coast[tuple(goal)]+=1
    else:
        map_coast[tuple(goal)]=2
    control_rec+=1

    return trace_router(pacman=pacman, goal=new_goal, map_coast=map_coast, control_rec=control_rec, get_pos=get_pos, ghosts_range=ghosts_range)

def high_ghost(pacman, moves, ghosts, second_objective, ghost_coast):
    move_coast=[0]*len(moves)                                                            
    second_goal=trace_router(pacman, second_objective, ghost_coast, get_pos = True)
    ghosts=set([tuple(g) for g in ghosts])  #consider ghosts in the same position as a single

    #get all the positions that the ghosts can reach you
    ghosts_predict=[trace_router(pacman, g ,get_pos=True, ghosts_range= 2.5*(calc_dist(pacman,g))**(1/2) ) \
                        for g in ghosts if calc_dist(pacman, g) <= 64]
    
    if second_goal not in ghosts_predict and tuple(second_goal) not in ghosts:
        return second_goal

    for i in range(len(moves)):
        for g in ghosts:
            dist = calc_dist(moves[i], g)
            if dist <= 2:
                move_coast[i] = 100         #prevent any problems of can cause ghost_coast 
            else:
                move_coast[i] += 1/(1+dist)
        if tuple(moves[i]) in ghost_coast:
            coast = ghost_coast[tuple(moves[i])]
        else:
            coast=1
        move_coast[i] = move_coast[i]*coast

    return moves[smaller_index(move_coast)]

async def agent_loop(server_address = "localhost:8000", agent_name="82783"):
    async with websockets.connect("ws://{}/player".format(server_address)) as websocket:
        # Receive information about static game properties 
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))
        msg = await websocket.recv()
        game_properties = json.loads(msg) 

        ghost_level = game_properties['ghosts_level']
        
        global mapa 
        mapa = Map(game_properties['map'])

        #init agent properties 
        lives=0

        while True: 
#************               receive state and check the End Game****************************************
           
            r = await websocket.recv()
            state = json.loads(r)
            if len(state) == 1:
                print(state['score'])
                return            
            if not state['lives']:
                print("GAME OVER")
                print(state['score'])
                return

#***********                alter or initiate the variables*******************************************
           
            if lives < state['lives']: #reset defalt values in each start game
                ghost_coast={}
                move_coast={}
                goal=[0,0]
                pacman=[0,0]
                scape=False
            
            lives=state['lives']

            cur_pos = pacman
            pacman = state['pacman']
            ghosts=[g[0] for g in state['ghosts'] if not g[1]]          #take all not zombie ghosts
            ghosts_zombie=[g[0] for g in state['ghosts'] if g[1]]
            time_zombie = next(( g[2] for g in state['ghosts'] if g[1]),0) #If any ghosts is zombie, take its time to change its mode

#***********                define the goal************************************************************
           
            if state['ghosts'] and calc_dist(pacman, smaller_cost(pacman, ghosts) ) <= 9:
                scape=True
                moves=[ k for k in generate_moves(pacman) if not mapa.is_wall(k)]

                    #run and hunter ghost
                if calc_dist(pacman, smaller_cost(pacman, ghosts_zombie)) < time_zombie**2:
                    second_objective = smaller_cost(pacman,ghosts_zombie)

                    #run and hunter booster
                elif state['boost'] and calc_dist(pacman, smaller_cost(pacman, state['boost'])) < 100:
                    second_objective = smaller_cost(pacman, state['boost'])
              
                    #run and hunter points
                elif state['energy']:
                    second_objective = smaller_cost(pacman, state['energy'])
                
                goal=high_ghost(pacman, moves, ghosts, second_objective, ghost_coast)
                
                if tuple(pacman) in ghost_coast:
                    ghost_coast[tuple(pacman)]+=1
                else:
                    ghost_coast[tuple(pacman)]=2
                   
            elif state['ghosts'] and calc_dist(pacman, smaller_cost(pacman,ghosts_zombie)) < time_zombie**2:
                goal=smaller_cost(pacman, ghosts_zombie)
                scape=False

            elif state['energy'] and goal not in state['energy']:
                goal = smaller_cost(pacman, state['energy'])
                scape=False
                if len(move_coast) > 25:       # reset if the goal is achieved
                    move_coast = {}            
           #else, goal is the same

#***********            load the lasts positions to coast map***************************************

            if tuple(pacman) in move_coast:
                move_coast[tuple(pacman)]+=1
            else:
                move_coast[tuple(pacman)]=2

#***********            define the goal************************************************************

            if scape:   
                key = trace_router(pacman = (pacman), goal = goal)
            else:
                cur_moves = [[x,y] for x,y in generate_moves(cur_pos) if not mapa.is_wall((x,y))]
                new_moves = [[x,y] for x,y in generate_moves(pacman) if not mapa.is_wall((x,y))]
                
                    #change the key if you you have a new possibility to move, or are blocked
                if len(cur_moves) < len(new_moves) or cur_pos == pacman:
                    key = trace_router(pacman = (pacman), goal = goal, map_coast = move_coast)
                if len(ghost_coast) > 25:
                    ghost_coast = {}

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
    parser.add_argument("--test", help="Name of the client", type= float, default=0)
    args = parser.parse_args()
    SERVER = args.server
    PORT = args.port 
    NAME = args.name
    global ARG 
    ARG = args.test
    LOOP =asyncio.get_event_loop()

    try:
        LOOP.run_until_complete(agent_loop("{}:{}".format(SERVER,PORT), NAME))
    finally:
        LOOP.stop()

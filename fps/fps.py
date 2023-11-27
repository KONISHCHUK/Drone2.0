#!/usr/bin/env python

import requests
import json
from random import randrange
from flask import Flask, request, jsonify
from cryptography.fernet import Fernet


CONTENT_HEADER = {"Content-Type": "application/json"}
DRONE_ENDPOINT_URI = "http://drone_communication_in:6073/set_command"
ATM_ENDPOINT_URI = "http://atm:6064/new_task"

drones = []

host_name = "0.0.0.0"
port = 6065
app = Flask(__name__)             # create an app instance

class Drone:

    def __init__(self, coordinate, name, psswd):
        self.coordinate = coordinate
        self.name = name
        self.psswd = psswd
        self.status = "Initiated"
        self.endpoint = DRONE_ENDPOINT_URI


def encrypt(data):
    key = b'tgbSXNRH_HbnAw6JWLPtz48eBxigUx8ERJLkbATjZzY='
    f = Fernet(key)
    encrypted_data = f.encrypt(data)
    return encrypted_data


@app.route("/set_command", methods=['POST'])
def set_command():
    content = request.json
    global drones
    try:
        if content['command'] == 'initiate':
            tmp = False
            for i in range(len(drones)):
                if drones[i].status == "Initiated" and tmp == False:
                    print(i)
                    tmp = True
                    drones[i].status = "Working"
                    drones[i].coordinate= content['coordinate']
                    drones[i].psswd = content['psswd']
                    drones[i].name = content['name']

                    data = {
                    "name": content['name'],
                    "command": "initiate",
                    "coordinate": content['coordinate'],
                    "psswd": content['psswd']
                    }

                    data = json.dumps(data)
                    data = data.encode()
                    data = encrypt(data)
                    
                    requests.post(
                        drones[i].endpoint,
                        data = data,
                        headers=CONTENT_HEADER,
                    )
                    print(f'[FPS_INITIATE]')
                    print(f'Successfully requested initiation for {content["name"]}')
            if tmp == False:
                print(f'[FPS_INITIATE_ERROR]')
                print(f'Not enough drones for this task')
        else:
            drone = drones[0]
            ###
            if content['command'] == 'start':
                data = {
                "name": content['name'],
                "command": content['command'],
                "psswd": content['psswd'],
                "speed": content['speed']
                }
                data = json.dumps(data)
                data = data.encode()
                data = encrypt(data)
                requests.post( 
                    drone.endpoint,
                    data=data,
                    headers=CONTENT_HEADER,
                )
                print(f'[FPS_START]')
                print(f'Requested start for {content["name"]} successfully')
            if content['command'] == 'stop':
                data = {
                "name": content['name'],
                "command": content['command'],
                "psswd": content['psswd']
                }
                data = json.dumps(data)
                data = data.encode()
                data = encrypt(data)
                requests.post(
                    drone.endpoint,
                    data=data,
                    headers=CONTENT_HEADER,
                )
                print(f'[FPS_STOP]')
                print(f'Requested stop for {content["name"]} successfully')
            if content['command'] == 'sign_out':
                drone.status = 'Initiated'
                #drones.remove(drone)
                data = {
                "name": content['name'],
                "command": content['command'],
                "psswd": content['psswd']
                }
                data = json.dumps(data)
                data = data.encode()
                data = encrypt(data)
                requests.post(
                    drone.endpoint,
                    data=data,
                    headers=CONTENT_HEADER,
                )
                print(f'[FPS_SIGN_OUT]')
                print(f'Requested sign_out for {content["name"]}')
            if content['command'] == 'new_task':
                data = {
                "name": content['name'],
                "points": content['points']
                }
                requests.post(
                    ATM_ENDPOINT_URI,
                    data=json.dumps(data),
                    headers=CONTENT_HEADER,
                )
                print(f'[FPS_NEW_TASK]')
                print(f'Requested new task for {content["name"]}')
            if content['command'] == 'register': 
                data = {
                "name": content['name'],
                "command": "register",
                "psswd": content['psswd']
                }
                data = json.dumps(data)
                data = data.encode()
                data = encrypt(data)
                requests.post(
                    drone.endpoint,
                    data=data,
                    headers=CONTENT_HEADER,
                )
                print(f'[FPS_REGISTER]')
                print(f'Successfully requested for {content["name"]}')
            if content['command'] == 'clear_flag': 
                data = {
                "name": content['name'],
                "command": "clear_flag",
                "psswd": content['psswd']
                }
                data = json.dumps(data)
                data = data.encode()
                data = encrypt(data)
                requests.post(
                    drone.endpoint,
                    data=data,
                    headers=CONTENT_HEADER,
                )
                print(f'[FPS_CLEAR_FLAG]')
                print(f'Successfully requested for drone {content["name"]}')

    except Exception as e:
        print(e)
        error_message = f"malformed request {request.data}"
        return error_message, 400
    return jsonify({"operation": "set_command", "status": True})

@app.route("/data_in", methods=['POST'])
def data_in():
    content = request.json

    global drones
    try:

        drone = drones[0]
        print(f'[FPS_DATA_IN]')
        
        if content['operation'] == 'log':
            if content['msg'] == "Task finished":
                drone.status = 'Initiated'
                print(f'{content["name"]} successfully finished!')
            else:
                print(f'Successfully received {content}')
        elif content['operation'] == 'data':
            print(f'Successfully received {content}')
    except Exception as _:
        error_message = f"malformed request {request.data}"
        return error_message, 400
    return jsonify({"operation": "new_task", "status": True})

@app.route("/atm_input", methods=['POST'])
def atm_input():
    content = request.json
    global drones
    try:

        if content['task_status'] == 'Accepted':
            data = {
               "name": content['name'],
               "points": content['points'],
               "command": 'set_task',
               "psswd": drones[0].psswd
            }
            data = json.dumps(data)
            data = data.encode()
            data = encrypt(data)
            requests.post(
                drones[0].endpoint,
                data=data,
                headers=CONTENT_HEADER,
            )
            print(f'[FPS_NEW_TASK]')
            print(f'Successfully accepted new task for {content["name"]}')
        else:
            print(f'[FPS_NEW_TASK_ERROR]') 
            print(f'Something went wrong during accepting new task for {content["name"]}') 

    except Exception as _:
        error_message = f"malformed request {request.data}"
        return error_message, 400
    return jsonify({"operation": "new_task", "status": True})


if __name__ == "__main__":


    tmp = Drone([0,0,0], "ITEM1", 12345)
    drones.append(tmp)
    print("Added drone " + tmp.name + " uri: " + tmp.endpoint)

    app.run(port = port, host=host_name)
    
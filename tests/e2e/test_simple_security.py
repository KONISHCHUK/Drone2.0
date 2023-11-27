
from multiprocessing import Process, Queue
import random
from time import sleep
from flask import Flask, jsonify, request
import json
import requests
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

host_name = "0.0.0.0"
port = 6162

REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "auth": "very-secure-token"
}

FPS_COMMAND_ENDPOINT_URI = 'http://0.0.0.0:6065/set_command'
ATM_COMMAND_ENDPOINT_URI =  'http://0.0.0.0:6064/set_area'

global_events_log = Queue()

app = Flask(__name__)

@app.route("/", methods=['POST'])
def data_receive():
    global global_events_log
    try:
        content = request.json
        logging.info(f"Received message: {content}")
        global_events_log.put(content)
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 400
    return jsonify({"status": True})

# Функция для запуска Flask-приложения
def run_app():
    app.run(port=port, host=host_name)
def initiate(name, coordinate, psswd):
    data = {
        "command": "initiate",
        "name": name,
        "coordinate": coordinate,
        "psswd": psswd
    }
    try:
        with requests.post(FPS_COMMAND_ENDPOINT_URI, data=json.dumps(data), headers=REQUEST_HEADERS) as response:
            response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Request failed: {e}")
        raise


def register(name, psswd):
    data = {
        "command" : "register",
        "name" : name, #"ITEM1",
        "psswd": psswd #12345
    }
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def set_area(area):
    data = {
        "area" : area #[-1,-1,100,100]
    }
    response = requests.post(
        ATM_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def start(name, speed, psswd):
    data = {
        "command" : "start",
        "name" : name, # "ITEM1",
        "speed" : speed, #1,
        "psswd": psswd #12345
    }
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def stop(name, psswd):
    data = {
        "command" : "stop",
        "name" : name, #"ITEM1",
        "psswd": psswd #12345
    }
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def sign_out(name, psswd):
    data = {
        "command" : "sign_out",
        "name" : name, #"ITEM1",
        "psswd": psswd #12345
    }
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def move_to(name, coordinate, speed, psswd):
    data = {
        "command" : "move_to",
        "name" : name, #"ITEM1",
        "coordinate" : coordinate, #[3,5,1],
        "speed" : speed, #1,
        "psswd": psswd #12345
    } 
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def new_task(name, points, psswd):
    data = {
        "command" : "new_task",
        "name" : name, #"ITEM1",
        "points" : points,#, [[5,5,5,0],[8,8,8,1],[11,11,11,1],[16,16,11,0]],
        "psswd": psswd #12345
    }
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200

def clear_flag(name, psswd):
    data = {
        "command" : "clear_flag",
        "name" : name, #"ITEM1",
        "psswd": psswd #12345
    }
    response = requests.post(
        FPS_COMMAND_ENDPOINT_URI,
        data=json.dumps(data),
        headers=REQUEST_HEADERS,
    )
    assert response.status_code == 200
    

###
### Security tests
###

def test_bad_psswrd():
    global global_events_log
    server = Process(target=run_app)
    server.start()

    initiate("ITEM1", [2,2,2], 12345)
    sleep(2)
    register("ITEM1", 12345)
    sleep(2)
    set_area([-1,-1,100,100])
    sleep(1)
    new_task("ITEM1", [[4,4,2,0],[3,7,2,1],[10,10,3,1]], 12345)
    sleep(3)
    start("ITEM1", 1, 123456)
    sleep(10)
    sign_out("ITEM1", 12345)
    sleep(5)

    # stop
    server.terminate()
    server.join()

    events_log = []
    try:
        # read
        while True:
            event = global_events_log.get_nowait()
            events_log.append(event)
    except Exception as _:
        # no events
        pass
        
    #print(f"list: {events_log}")
    assert len(events_log) == 0


def test_bad_coord():
    global global_events_log
    server = Process(target=run_app)
    server.start()

    initiate("ITEM1", [200,200,2], 12345)
    sleep(3)
    register("ITEM1", 12345)
    sleep(3)
    set_area([-1,-1,100,100])
    sleep(3)
    new_task("ITEM1", [[4,4,2,0],[3,7,2,1],[10,10,3,1]], 12345)
    sleep(5)
    start("ITEM1", 1, 12345)
    sleep(10)
    sign_out("ITEM1", 12345)
    sleep(5)

    # stop
    server.terminate()
    server.join()
    
    events_log = []
    try:
        # read
        while True:
            event = global_events_log.get_nowait()
            events_log.append(event)
    except Exception as _:
        # no events
        pass
        
    #print(f"list: {events_log}")
    assert len(events_log) < 20
    stop_flag = False

    for i in events_log:
        if 'emergency_stop' in i: 
            stop_flag = True
    assert stop_flag == True
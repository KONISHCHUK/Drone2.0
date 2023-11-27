
from multiprocessing import Process, Queue
from time import sleep
from flask import Flask, jsonify, request
import json
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Изменение порта для тестового Flask-приложения
test_port = 6063
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "auth": "very-secure-token"
}

FPS_COMMAND_ENDPOINT_URI = 'http://0.0.0.0:6065/set_command'
ATM_COMMAND_ENDPOINT_URI = 'http://0.0.0.0:6064/set_area'

global_events_log = Queue()

app = Flask(__name__)

@app.route("/", methods=['POST'])
def data_receive():
    global global_events_log
    try:
        content = request.json
        logging.info(f"Received request: {content}")
        global_events_log.put(content)
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 400
    return jsonify({"status": True})

# Функция для запуска Flask-приложения на другом порту
def run_app():
    app.run(port=test_port, host=host_name)

def send_request(url, data):
    """ Функция для отправки запроса с логированием """
    response = requests.post(url, data=json.dumps(data), headers=REQUEST_HEADERS)
    logging.info(f"Sent request to {url}: {data}")
    logging.info(f"Received response: {response.status_code}, {response.text}")
    return response


def initiate(name, coordinate, psswd):
    # По аналогии с этой функцией, добавьте функции для остальных операций
    data = {
        "command": "initiate",
        "name": name,
        "coordinate": coordinate,
        "psswd": psswd
    }
    response = send_request(FPS_COMMAND_ENDPOINT_URI, data)
    assert response.status_code == 200
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
### Functionally tests
###

def test_single_full_functionality():
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
    start("ITEM1", 1, 12345)
    sleep(35)
    sign_out("ITEM1", 12345)
    sleep(1)

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
    assert len(events_log) > 20
    assert events_log[random.randint(0,len(events_log)-1)]['token'] != ''
    x_reached = False
    y_reached = False
    z_reached = False

    for i in events_log:
        if i['coordinate_x'] > 9: 
            x_reached = True
        if i['coordinate_y'] > 9: 
            y_reached = True    
        if i['coordinate_z'] == 3: 
            z_reached = True
    assert (x_reached & y_reached & z_reached) == True
    assert ((abs(events_log[len(events_log)-1]['coordinate_x'] - 2) <= 1) & (abs(events_log[len(events_log)-1]['coordinate_y'] - 2) <= 1)) == True







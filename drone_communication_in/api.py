#!/usr/bin/env python

from random import randrange
import threading
from uuid import uuid4
from flask import Flask, request, jsonify
from producer import proceed_to_deliver

CONTENT_HEADER = {"Content-Type": "application/json"}
ATM_ENDPOINT_URI = "http://atm:6064/data_in"
ATM_SIGN_UP_URI = "http://atm:6064/sign_up"
ATM_SIGN_OUT_URI = "http://atm:6064/sign_out"
FPS_ENDPOINT_URI = "http://fps:6065/data_in"
DELIVERY_INTERVAL_SEC = 1
drones = []

host_name = "0.0.0.0"
port = 6073
app = Flask(__name__)             # create an app instance


@app.route("/set_command", methods=['POST'])
def set_command():
    try:
        
        content = request.data
        content = content.decode()
        
        req_id = uuid4().__str__()
        msg = {
            "id": req_id,
            "operation": "in",
            "deliver_to": "drone_ccu",
            "source": "drone_communication_in",
            "msg": content
            }
        proceed_to_deliver(req_id, msg)
        
    except Exception as e:
        print(e)
        error_message = f"malformed request {request.data}"
        return error_message, 400
    return jsonify({"status": True})
    
def start_rest(requests_queue):
    global _requests_queue 
    _requests_queue = requests_queue
    threading.Thread(target=lambda: app.run(host=host_name, port=port, debug=True, use_reloader=False)).start()

if __name__ == "__main__":        # on running python app.py
    start_rest()
    
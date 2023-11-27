# implements Kafka topic consumer functionality

from datetime import datetime
import multiprocessing
import threading

import requests
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver


_requests_queue: multiprocessing.Queue = None

CONTENT_HEADER = {"Content-Type": "application/json"}
ATM_ENDPOINT_URI = "http://atm:6064/data_in"
ATM_WATCHDOG_URI = "http://atm:6064/watchdog"
ATM_SIGN_UP_URI = "http://atm:6064/sign_up"
ATM_SIGN_OUT_URI = "http://atm:6064/sign_out"
FPS_ENDPOINT_URI = "http://fps:6065/data_in"

def handle_event(id, details_str):
    details = json.loads(details_str)
    #print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    
    try:
        delivery_required = False
        if details['operation'] == 'send_position':
            data = {
            "name": details['name'],
            "token": details['token'],
            "coordinate": details['coordinate'],
            "coordinate_x": details['coordinate'][0],
            "coordinate_y": details['coordinate'][1],
            "coordinate_z": details['coordinate'][2]
            }
            try:
                response = requests.post(
                    ATM_ENDPOINT_URI,
                    data=json.dumps(data),
                    headers=CONTENT_HEADER,
                )
            except Exception as e:
                print(f'exception raised: {e}')
        elif details['operation'] == 'register':
            data = {
                "name": details['name'],
                "coordinate": details['coordinate'],
                "status": "OK"
                }
            try:
                response = requests.post(
                    ATM_SIGN_UP_URI,
                    data=json.dumps(data),
                    headers=CONTENT_HEADER,
                )
            except Exception as e:
                print(f'exception raised: {e}')
        elif details['operation'] == 'sign_out':
            data = {
                "name": details['name']
                }
            try:
                response = requests.post(
                    ATM_SIGN_OUT_URI,
                    data=json.dumps(data),
                    headers=CONTENT_HEADER,
                )
            except Exception as e:
                print(f'exception raised: {e}')
        elif details['operation'] == 'watchdog':
            data = {}
            try:
                response = requests.post(
                    ATM_WATCHDOG_URI,
                    data=json.dumps(data),
                    headers=CONTENT_HEADER,
                )
            except Exception as e:
                print(f'exception raised: {e}')
        elif details['operation'] == 'log':
            data = {
                "name": details['name'],
                "operation": "log",
                "msg": details['msg']
            }
            try:
                response = requests.post(
                FPS_ENDPOINT_URI,
                data=json.dumps(data),
                headers=CONTENT_HEADER,
            )
            except Exception as e:
                print(f'exception raised: {e}') 
        elif details['operation'] == 'data':
            try:
                data = {
                "name": details['name'],
                "operation": "data",
                "percent": details['percent'],
                }
                response = requests.post(
                    FPS_ENDPOINT_URI,
                    data=json.dumps(data),
                    headers=CONTENT_HEADER,
                )
            except Exception as e:
                print(f'exception raised: {e}')
        else:
            print(f"[warning] unknown operation in communication_out!\n{details}")                
        if delivery_required:
            proceed_to_deliver(id, details)
    except Exception as e:
        print(f"[error] failed to handle request: {e}")
    


def consumer_job(args, config, requests_queue: multiprocessing.Queue):
    # Create Consumer instance
    consumer = Consumer(config)

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            consumer.assign(partitions)

    # Subscribe to topic
    topic = "drone_communication_out"
    consumer.subscribe([topic], on_assign=reset_offset)

    # Poll for new messages from Kafka and print them.
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                pass
            elif msg.error():
                print(f"[error] {msg.error()}")
            else:
                try:
                    id = msg.key().decode('utf-8')
                    details_str = msg.value().decode('utf-8')
                    handle_event(id, details_str)
                except Exception as e:
                    print(
                        f"[error] Malformed event received from topic {topic}: {msg.value()}. {e}")
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()


def start_consumer(args, config, requests_queue):
    global _requests_queue
    _requests_queue = requests_queue
    threading.Thread(target=lambda: consumer_job(args, config, requests_queue)).start()


if __name__ == '__main__':
    start_consumer(None)
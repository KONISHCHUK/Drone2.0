# implements Kafka topic consumer functionality

from datetime import datetime
import multiprocessing
import threading
import time
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver
from cryptography.fernet import Fernet

_requests_queue: multiprocessing.Queue = None

DELIVERY_INTERVAL_SEC = 1

start_point = []
coordinate = []
name = ''
psswd = 12345 
emergency_stop = threading.Event()
token = ''
motion_status = "Stopped"
task_points = []
camera_status = "OFF"
camera_event = threading.Event()
status = 'Active'
hash = ''
watchdog_time = time.time()
speed = 1

def decrypt(msg, key):
    f = Fernet(key)
    return f.decrypt(msg)

# Аварийная остановка.
def emergency(details):
        global motion_status
        details['operation'] = "stop"
        details['deliver_to'] = "drone_flight_controller"
        proceed_to_deliver(details['id'], details)
        motion_status = "Stopped"


def clear_emergency_flag(details):
        if not status == "Blocked":
            details['operation'] = "clear"
            details['name'] = name
            details['deliver_to'] = "drone_flight_controller"
            proceed_to_deliver(details['id'], details)


# Дрон летит, пока диспетчерская подтверждает его право на это.
def watchdog(details):
    if (time.time() - watchdog_time) > 2:
        try:
            details['operation'] = "watchdog"
            details['deliver_to'] = "drone_communication_out"
            proceed_to_deliver(details['id'], details)
        except Exception as e:
            print(e)
    if (time.time() - watchdog_time) > 10:
        emergency(details)


# Проверка на триггерные точки - точки включения камеры, возврата на базу.
def position_controller(details):
    global camera_status
    if len(task_points) != 0:
        if task_points[0][3] == 1 and camera_status == 'OFF':
            camera_status = 'ON'
            details['operation'] = "camera_on"
            details['name'] = name
            details['deliver_to'] = "drone_data_aggregation"
            proceed_to_deliver(details['id'], details)
        elif task_points[0][3] != 1 and camera_status == 'ON':
            camera_status = 'OFF'
            details['operation'] = "camera_off"
            details['name'] = name
            details['deliver_to'] = "drone_data_aggregation"
            proceed_to_deliver(details['id'], details)
    if (abs(coordinate[0] - start_point[0]) < 1) and (abs(coordinate[1] - start_point[1]) < 1) and len(task_points) == 0:
        end_task(details)
    

def end_task(details):
    try:
        details['operation'] = "camera_off"
        details['deliver_to'] = "drone_data_aggregation"
        proceed_to_deliver(details['id'], details)

        time.sleep(1)

        data = {
        "id": details['id'],
        "name": name,
        "operation": "log",
        "deliver_to": "drone_communication_out",
        "source": "drone_ccu",
        "msg": "Task finished"
        }
        proceed_to_deliver(details['id'], data)

    except Exception as e:
        print(f'exception raised: {e}')


def start(details):
    x = task_points[0][0]
    y = task_points[0][1]
    z = task_points[0][2]

    if abs(coordinate[0] - x) <= 1 and abs(coordinate[1] - y) <= 1 and abs(coordinate[2] - z) <= 1:
        task_points.pop(0)
        clear_emergency_flag(details)

    time.sleep(1)

    if not len(task_points) == 0:
        details['operation'] = "move_to"
        details['deliver_to'] = "drone_flight_controller"
        details['dest_point'] = task_points[0]
        details['coordinate'] = coordinate
        details['speed'] = speed
        proceed_to_deliver(details['id'], details)

        time.sleep(1)

        msg = {
            "id": details['id'],
            "operation": "get_status",
            "deliver_to": "drone_diagnostic",
            "source": "drone_ccu"
            }
        proceed_to_deliver(details['id'], msg)

    if len(task_points) == 0: # return to home
        time.sleep(DELIVERY_INTERVAL_SEC)
        clear_emergency_flag(details)
        details['operation'] = "move_to"
        details['deliver_to'] = "drone_flight_controller"
        details['dest_point'] = start_point
        details['coordinate'] = coordinate
        details['speed'] = 1

def handle_event(id, details_str):
    details = json.loads(details_str)
    #print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    
    try:
        delivery_required = False
        global watchdog_time, coordinate, name, psswd, start_point, token, hash, status, task_points, camera_event, emergency_stop, motion_status, speed
        if details['operation'] == 'in':
            key = b'tgbSXNRH_HbnAw6JWLPtz48eBxigUx8ERJLkbATjZzY='
            msg = details['msg'].encode()
            msg = decrypt(msg, key)
            msg = msg.decode()
            msg = json.loads(msg)
            if msg['command'] == 'initiate':
                coordinate = msg['coordinate']
                start_point = coordinate[:]
                name = msg['name']
                psswd = msg['psswd']
                print (f"Added in point {coordinate}")
            elif msg['command'] == 'set_token':
                token = msg['token']
                print(f'[DRONE_TOKEN_SET]')
            elif msg['command'] == 'task_status_change':
                if token == msg['token']:
                    task_status = msg['task_status']
                    hash = msg['hash']
                    print(f'[DRONE_TASK_ACCEPTED]') 
            elif msg['command'] == 'watchdog':
                #print("Watchdog")
                watchdog_time = msg['time']
            elif msg['command'] == 'emergency_stop':
                if msg['token'] == token:
                    status = "Blocked"
                    emergency(details)
                    print(f"[ATTENTION]")
                    print(f"{name} emergency stopped!")
            elif psswd == msg['psswd']:
                if msg['command'] == 'register':
                    details['operation'] = "register"
                    details['deliver_to'] = "drone_communication_out"
                    details['name'] = name
                    details['coordinate'] = coordinate
                    delivery_required = True
                elif msg['command'] == 'set_task':
                    if hash == len(msg["points"]):
                        print(f'[DRONE_SET_TASK]')
                        print(f'Point added!')
                        task_points = msg["points"]
                elif msg['command'] == 'start':
                    clear_emergency_flag(details)
                    watchdog_time = time.time()
                    camera_event.clear()
                    speed = msg['speed']
                    start(details)
                elif msg['command'] == 'stop':
                    emergency(details)
                    print("Stopped")
                elif msg['command'] == 'sign_out':
                    emergency(details)
                    details['operation'] = "sign_out"
                    details['name'] = name
                    details['deliver_to'] = "drone_communication_out"
                    status = 'Active'
                    delivery_required = True
            else:
                print(f"[warning] unknown command in ccu_in!\n{msg}")     
        elif details['operation'] == 'diagnostic_status':
            if details['battery_status'] < 20:
                print(f'[BATTRE_LOW]')
        elif details['operation'] == 'gps_coordinate':
            coordinate = details['coordinate']
            print (details['coordinate'])
            position_controller(details)
        elif details['operation'] == 'ins_coordinate':
            #coordinate = details['coordinate']
            
            msg = {
            "id": details['id'],
            "operation": "send_position",
            "token": token,
            "deliver_to": "drone_communication_out",
            "source": "drone_ccu",
            "name": name,
            "coordinate": coordinate
            }
            proceed_to_deliver(details['id'], msg)
            watchdog(details)
        elif details['operation'] == 'data':
            details['deliver_to'] = "drone_communication_out"
            delivery_required = True
        elif details['operation'] == 'reached':
            #clear_emergency_flag(details)
            start(details)
        else:
            print(f"[warning] unknown operation in ccu!\n{details}")                
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
    topic = "drone_ccu"
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

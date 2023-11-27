# implements Kafka topic consumer functionality

from datetime import datetime
import math
import multiprocessing
import threading
import time
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver


_requests_queue: multiprocessing.Queue = None
DELIVERY_INTERVAL_SEC = 1
emergency_stop = threading.Event()
coordinate = []

# Вообще, такого быть не должно. Но т.к. gps получает данные со спутника,
# а ins считает внутри себя, то для этой задачи можно отдавать им фактическое
# перемещение отсюда. 
def send_position(details, coordinate):
    msg = {
        "id": details['id'],
        "operation": "get_coordinate",
        "deliver_to": "drone_gps",
        "source": "drone_flight_controller",
        "coordinate": coordinate
        }
    #_requests_queue.put(msg)
    proceed_to_deliver(details['id'], msg)
    print(coordinate)

    details['deliver_to'] = 'drone_ins'
    details['operation'] = 'get_coordinate'
    details['coordinate'] = coordinate
    proceed_to_deliver(details['id'], details)


def move_to(details, x, y, z, direction, speed, time_offset):
    global emergency_stop, coordinate
    while not emergency_stop.is_set():
        if abs(coordinate[2] - z) >= 1:
            time.sleep(1)
            if (coordinate[2] - z) >= 0:
                coordinate[2] -= 1
            else: 
                coordinate[2] += 1
            send_position(details, coordinate)
        else:
            if time_offset == 0:
                if (abs(coordinate[0] - x) > 1) or (abs(coordinate[1] - y) > 1):
                    time.sleep(DELIVERY_INTERVAL_SEC)
                    coordinate[0] += math.cos(direction) * speed * DELIVERY_INTERVAL_SEC
                    coordinate[1] += math.sin(direction) * speed * DELIVERY_INTERVAL_SEC
                    send_position(details, coordinate)
                else:
                    emergency_stop.set()
                    motion_status = "Stopped"
                    print(f'[REACHED_POINT] {coordinate}')
                    send_position(details, coordinate)
                    time.sleep(1)
                    details['operation'] = "reached"
                    details['deliver_to'] = "drone_ccu"
                    proceed_to_deliver(details['id'], details)
            else:
                if (abs(coordinate[0] - x) > 1) or (abs(coordinate[1] - y) > 1):
                    time.sleep(time_offset)
                    coordinate[0] += math.cos(direction) * speed * DELIVERY_INTERVAL_SEC
                    coordinate[1] += math.sin(direction) * speed * DELIVERY_INTERVAL_SEC
                    send_position(details, coordinate)
                else:
                    emergency_stop.set()
                    motion_status = "Stopped"
                    print(f'[REACHED_POINT] {coordinate}')
                    send_position(details, coordinate)
                    time.sleep(1)
                    details['operation'] = "reached"
                    details['deliver_to'] = "drone_ccu"
                    proceed_to_deliver(details['id'], details)
                time_offset=0
        
        data = {
        "id": details['id'],
        "deliver_to": 'drone_battery_control',
        "operation": "change_battery",
        "source": "drone_flight_controller",
        "delta": -1
        }
        proceed_to_deliver(details['id'], data)
        


def handle_event(id, details_str):
    details = json.loads(details_str)
    #print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    global emergency_stop, coordinate
    try:
        delivery_required = False
        if details['operation'] == 'move_to':
            motion_status = "Active"
            global DELIVERY_INTERVAL_SEC
            coordinate = details['coordinate']
            speed = details['speed']
            dest_point = details['dest_point']
            x = dest_point[0]
            y = dest_point[1]
            z = dest_point[2]
            dx_target = x - coordinate[0]
            dy_target = y - coordinate[1]
            dz_target = z - coordinate[2]
            direction = math.atan2(dy_target, dx_target)
            t = math.sqrt(dx_target**2 + dy_target**2)/speed
            time_offset = t%DELIVERY_INTERVAL_SEC
            
            threading.Thread(target=lambda:  move_to(details, x, y, z, direction, speed, time_offset)).start()
            details['operation'] = 'smth'
            details['deliver_to'] = 'drone_engines'
            delivery_required = True
        elif details['operation'] == 'stop':
            emergency_stop.set()
        elif details['operation'] == 'clear':
            emergency_stop.clear()
        else:
            print(f"[warning] unknown operation in flight_controller!\n{details}")                
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
    topic = "drone_flight_controller"
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

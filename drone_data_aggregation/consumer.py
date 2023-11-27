# implements Kafka topic consumer functionality

from datetime import datetime
import multiprocessing
import os
import threading
import time
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver


_requests_queue: multiprocessing.Queue = None
camera_event = threading.Event()
camera_status = "OFF"

DELIVERY_INTERVAL_SEC = 3

def telemetry(details):
    print(f'[DRONE_CAMERA_ON]')
    global camera_status, camera_event
    while not camera_event.is_set():
        time.sleep(DELIVERY_INTERVAL_SEC)
        
        percent = 0
        if os.path.exists("/storage/tmp.jpeg"):
            im = Image.open("tmp.jpeg")
            pixels = im.load()  # список с пикселями
            x, y = im.size  # ширина (x) и высота (y) изображения

            white_pix = 0
            another_pix = 0

            for i in range(x):
                for j in range(y):
                    for q in range(3):
                        # проверка чисто белых пикселей, для оттенков нужно использовать диапазоны
                        if pixels[i, j][q]  > 240: #!= 255:  # pixels[i, j][q] > 240  # для оттенков
                            another_pix += 1
                        else:
                            white_pix += 1

            try:
                percent = round(white_pix / another_pix * 100, 3)
                print(percent)
            except ZeroDivisionError:
                print("Белых пикселей нет")

        msg = {
            "id": details['id'],
            "operation": "data",
            "deliver_to": "drone_ccu",
            "source": "drone_data_aggregation",
            "name": details['name'],
            "percent": percent
            }
        
        #Можно раскомментить, внутри заглушка. Просто будет еще немного лишней информации в логе.
        print("DATA_AGGREGATION")
        # proceed_to_deliver(details['id'], msg)

        # details['deliver_to'] = 'drone_data_saver'
        # details['operation'] = 'smth'
        # proceed_to_deliver(details['id'], details)


def handle_event(id, details_str):
    details = json.loads(details_str)
    #print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    
    global camera_event, camera_status
    try:
        delivery_required = False
        if details['operation'] == 'camera_on':
            camera_status = 'ON'
            camera_event.clear()
            threading.Thread(
                    target=lambda: telemetry(details)).start()
        elif details['operation'] == 'camera_off':
            camera_status = 'OFF'
            camera_event.set()
            print(f'[DRONE_CAMERA_OFF]')
        else:
            print(f"[warning] unknown operation in data_aggregation!\n{details}")                
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
    topic = "drone_data_aggregation"
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

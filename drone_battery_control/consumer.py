# implements Kafka topic consumer functionality

from datetime import datetime
import multiprocessing
import threading
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver


_requests_queue: multiprocessing.Queue = None
battery_charge = 100

def handle_event(id, details_str):
    details = json.loads(details_str)
    #print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    
    try:
        delivery_required = False
        global battery_charge
        if details['operation'] == 'get_battery':
            details['operation'] = 'battery_status'
            details['deliver_to'] = 'drone_diagnostic'
            details['battery_status'] = battery_charge
            delivery_required = True
        elif details['operation'] == 'change_battery':
            battery_charge += details['delta']
        else:
            print(f"[warning] unknown operation in battery_control!\n{details}")                
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
    topic = "drone_battery_control"
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
import sys, os
import json
import websocket

from celery import shared_task
import time
import threading
import queue


CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(CURRENT_DIR, "..")
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
import django

django.setup()


from apps.executor.models import Worker

print(Worker.objects.all())


import sys, signal


def signal_handler(signal, frame):
    print("\nBye bye!")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)

counter = 0


q = queue.Queue()


def worker():
    while True:
        item = q.get()
        print(f"Working on {item}")
        time.sleep(10)
        print(f"Finished {item}")
        q.task_done()


threading.Thread(target=worker, daemon=True).start()


def on_open(ws):

    print(">> on_open")

    ws.send(json.dumps({"msg": "Worker is ready", "state": "started"}))


def on_message(wsapp, message):
    global counter
    print(">> on_message")
    print(message, counter)
    q.put(json.dumps({"counter": counter}))
    counter += 1


def on_pong(wsapp, message):
    global counter
    print("pong", counter)
    counter += 1
    # if counter > 2:
    #    sys.exit()


def on_error(ws, message):
    print("on_error", message)


def on_close(ws, close_status_code, close_msg):
    print(
        "######################################### closed ###",
        close_status_code,
        close_msg,
    )


MIN_RUN_TIME = 10  # ws should run more time than this to be considered as live
RECONNECT_WAIT_TIME = 10
CONNECT_MAX_TRIES = 2
connect_tries = 0

session_id = "example-session"
notebook_id = 2


def worker_starting():
    workers = Worker.objects.filter(session_id=session_id)


while True:
    start_time = time.time()
    wsapp = websocket.WebSocketApp(
        f"ws://127.0.0.1:8000/ws/execute/{session_id}/worker/{notebook_id}/",
        on_message=on_message,
        on_pong=on_pong,
        on_close=on_close,
        on_open=on_open,
        on_error=on_error,
    )
    wsapp.run_forever(ping_interval=2, ping_timeout=1)
    end_time = time.time()

    # if ws running less than 10 seconds then something is wrong
    # we will try to connect again
    if end_time - start_time < MIN_RUN_TIME:
        print("Cant connect worker ...")
        connect_tries += 1
    else:
        connect_tries = 0
    if connect_tries >= CONNECT_MAX_TRIES:
        print("Stop worker")
        sys.exit(0)

    time.sleep(RECONNECT_WAIT_TIME)

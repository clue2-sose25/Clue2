import random
import logging
import uuid
import threading
import signal
import os
from locust import HttpUser, task, between, events

logging.getLogger().setLevel(logging.INFO)

max_requests = int(os.getenv("MAXIMUM_REQUESTS", 1000))
request_count = 0
stopped = False
quitting = False

lock = threading.Lock()

CATEGORIES = [
    "1",  # Electronics
    "2",  # Toys
    "3",  # Games
]

PRODUCTS = [
    "1",  # Robot Toy
    "2",  # Racing Car
    "3",  # Puzzle Game
]

def check_maximum_and_quit():
    global request_count
    global stopped
    with lock:
        if request_count >= max_requests:
            stopped = True
            signal.raise_signal(signal.SIGTERM)

@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response,
                       context, exception, start_time, url, **kwargs):
    global request_count
    with lock:
        request_count += 1
    check_maximum_and_quit()

class FixedRequestToyStoreUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = str(uuid.uuid4())

    @task
    def complete_user_journey(self):
        global stopped
        global request_count

        if stopped:
            self.environment.process_exit_code = 0
            self.environment.runner.stop()
            logging.info(f"Reached task limit {request_count}, quitting")
            return
        
        logging.info(f"Starting ToyStore user journey {request_count}")
        
        self.browse_home()
        
        for _ in range(random.randint(1, 2)):
            self.browse_categories()
        
        for _ in range(random.randint(1, 3)):
            self.browse_toys()
        
        if random.choice([True, False]):
            for _ in range(random.randint(1, 2)):
                if random.choice([True, False]):
                    self.browse_categories()
                else:
                    self.browse_toys()
        
        logging.info("Completed ToyStore user journey.")
        check_maximum_and_quit()

    def browse_home(self):
        if stopped:
            return
        self.client.get("/")

    def browse_categories(self):
        if stopped:
            return
        category_id = random.choice(CATEGORIES)
        self.client.get(f"/category/{category_id}")

    def browse_toys(self):
        if stopped:
            return
        product_id = random.choice(PRODUCTS)
        self.client.get(f"/toy/{product_id}")
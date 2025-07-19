import random
import logging
import uuid
import math
import os
from locust import HttpUser, task, between, LoadTestShape

logging.getLogger().setLevel(logging.INFO)

STAGE_DURATION = int(os.getenv("STAGE_DURATION", 300))
MAX_USERS = int(os.getenv("MAX_USERS", 100))
NUM_STAGES = int(os.getenv("NUM_STAGES", 8))

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

class ToyStoreRampUpLoadShape(LoadTestShape):
    def __init__(self):
        super().__init__()
        
        self.stage_duration = STAGE_DURATION
        
        self.stages = [
            {"users_percentage": 0.05},  # 5% - warm up
            {"users_percentage": 0.15},  # 15% - early traffic
            {"users_percentage": 0.30},  # 30% - building up
            {"users_percentage": 0.50},  # 50% - moderate load
            {"users_percentage": 0.75},  # 75% - high load
            {"users_percentage": 1.00},  # 100% - peak load
            {"users_percentage": 0.60},  # 60% - cooling down
            {"users_percentage": 0.20},  # 20% - low traffic
        ]
        
        self.num_stages = len(self.stages)

    def tick(self):
        run_time = self.get_run_time()
        
        current_stage_index = math.floor(run_time / self.stage_duration)
        
        if current_stage_index >= self.num_stages:
            return None
        
        stage_run_time = run_time - (current_stage_index * self.stage_duration)
        
        kill_time = min(max((self.stage_duration / 10), 2), 30)
        
        # If we're near the end of a stage, reduce users to 0 for clean transition
        if stage_run_time > self.stage_duration - kill_time:
            if current_stage_index == self.num_stages - 1:
                return None  # Terminate after all stages are done
            return (0, 100)  # Kill users before next stage
        
        try:
            stage = self.stages[current_stage_index]
        except IndexError:
            logging.error(f"Stage index {current_stage_index} out of range, num_stages: {self.num_stages}")
            return (0, 100)
        
        # Calculate target user count for this stage
        target_users = int(MAX_USERS * stage["users_percentage"])
        
        # Calculate spawn rate (users per second)
        # Higher spawn rate for smaller user counts, lower for larger
        spawn_rate = max(2, min(100, MAX_USERS / 10))
        
        logging.info(f"ToyStore Stage {current_stage_index + 1}/{self.num_stages}: "
                    f"{target_users} users ({stage['users_percentage']*100:.0f}% of max)")
        
        return (target_users, spawn_rate)

class RampUpToyStoreUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        self.session_id = str(uuid.uuid4())

    @task(20)
    def browse_home(self):
        self.client.get("/")

    @task(15)
    def browse_categories(self):
        category_id = random.choice(CATEGORIES)
        self.client.get(f"/category/{category_id}")

    @task(12)
    def browse_toys(self):
        product_id = random.choice(PRODUCTS)
        self.client.get(f"/toy/{product_id}")

    @task(8)
    def multi_category_browse(self):
        categories_to_browse = random.sample(CATEGORIES, random.randint(1, len(CATEGORIES)))
        for category_id in categories_to_browse:
            self.client.get(f"/category/{category_id}")

    @task(6)
    def multi_product_browse(self):
        products_to_browse = random.sample(PRODUCTS, random.randint(1, len(PRODUCTS)))
        for product_id in products_to_browse:
            self.client.get(f"/toy/{product_id}")

    @task(5)
    def comparison_shopping(self):
        products_to_compare = random.sample(PRODUCTS, min(len(PRODUCTS), random.randint(2, 3)))
        for product_id in products_to_compare:
            self.client.get(f"/toy/{product_id}")
        
        categories_to_check = random.sample(CATEGORIES, min(len(CATEGORIES), random.randint(1, 2)))
        for category_id in categories_to_check:
            self.client.get(f"/category/{category_id}")

    @task(3)
    def extended_browsing_session(self):
        for _ in range(random.randint(3, 6)):
            action = random.choice(['home', 'category', 'product'])
            
            if action == 'home':
                self.client.get("/")
            elif action == 'category':
                category_id = random.choice(CATEGORIES)
                self.client.get(f"/category/{category_id}")
            else:
                product_id = random.choice(PRODUCTS)
                self.client.get(f"/toy/{product_id}")
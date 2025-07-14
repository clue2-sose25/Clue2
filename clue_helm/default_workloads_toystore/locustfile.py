import random
import logging
import uuid
import time
from locust import HttpUser, task, between

logging.getLogger().setLevel(logging.INFO)

# ToyStore product and category data
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

class ToyStoreUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = str(uuid.uuid4())
        logging.info(f"Starting ToyStore user session: {self.session_id}")

    @task(15)
    def browse_home(self):
        self.client.get("/")

    @task(12)
    def browse_categories(self):
        category_id = random.choice(CATEGORIES)
        self.client.get(f"/category/{category_id}")

    @task(10)
    def browse_toys(self):
        product_id = random.choice(PRODUCTS)
        self.client.get(f"/toy/{product_id}")

    @task(8)
    def complete_user_journey(self):
        logging.info("Starting complete user journey")
        
        self.browse_home()
        
        for _ in range(random.randint(1, 3)):
            self.browse_categories()
        
        for _ in range(random.randint(1, 4)):
            self.browse_toys()
        
        self.wait()
        
        if random.random() < 0.3:
            for _ in range(random.randint(1, 2)):
                self.browse_categories()
                self.browse_toys()
        
        logging.info("Completed user journey")

    @task(5)
    def search_behavior(self):
        for _ in range(random.randint(2, 5)):
            if random.choice([True, False]):
                self.browse_categories()
            else:
                self.browse_toys()

    @task(3)
    def comparison_shopping(self):
        products_to_compare = random.sample(PRODUCTS, min(len(PRODUCTS), random.randint(2, 3)))
        for product_id in products_to_compare:
            self.client.get(f"/toy/{product_id}")
        
        categories_to_check = random.sample(CATEGORIES, min(len(CATEGORIES), random.randint(1, 2)))
        for category_id in categories_to_check:
            self.client.get(f"/category/{category_id}")

    @task(2)
    def deep_browsing_session(self):
        logging.info("Starting deep browsing session")
        
        for _ in range(random.randint(5, 8)):
            action = random.choice(['home', 'category', 'product'])
            
            if action == 'home':
                self.browse_home()
            elif action == 'category':
                self.browse_categories()
            else:
                self.browse_toys()
            
            # Use a shorter wait time during deep browsing
            time.sleep(random.uniform(0.5, 1.5))
        
        logging.info("Completed deep browsing session")

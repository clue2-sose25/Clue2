#!/usr/bin/python

# Ramp-up Load Shape for OpenTelemetry Demo
# Based on the teastore loadshapes.py pattern
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
import logging
import uuid
import math
import os
from locust import HttpUser, task, between, LoadTestShape

# Set up logging
logging.getLogger().setLevel(logging.INFO)

# Configuration from environment variables
STAGE_DURATION = int(os.getenv("STAGE_DURATION", 300))  # 5 minutes per stage
MAX_USERS = int(os.getenv("MAX_USERS", 100))
NUM_STAGES = int(os.getenv("NUM_STAGES", 8))

# Actual product IDs from the OpenTelemetry Demo
PRODUCT_IDS = [
    "OLJCESPC7Z",  # Vintage Typewriter
    "66VCHSJNUP",  # Vintage Camera Lens  
    "1YMWWN1N4O",  # Home Barista Kit
    "L9ECAV7KIM",  # Loafers
    "2ZYFJ3GM2N",  # Tank Top
    "0PUK6V6EV0",  # Vintage Record Player
    "LS4PSXUNUM",  # Metal Camping Mug
    "9SIQT8TOJO",  # City Bike
    "6E92ZMYYFZ"   # Air Plant
]

CURRENCIES = ["USD", "EUR", "CAD", "JPY", "GBP"]

class RampUpLoadShape(LoadTestShape):
    """
    Load shape that gradually ramps up users over multiple stages
    Simulates realistic traffic patterns with gradual increase and decrease
    """
    
    def __init__(self):
        super().__init__()
        
        self.stage_duration = STAGE_DURATION
        
        # Define load stages as percentage of max users
        # Gradual ramp up, peak, and ramp down
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
        """
        Define the load pattern over time
        Returns tuple of (user_count, spawn_rate) or None to stop
        """
        run_time = self.get_run_time()
        
        # Calculate current stage
        current_stage_index = math.floor(run_time / self.stage_duration)
        
        # Check if we've completed all stages
        if current_stage_index >= self.num_stages:
            return None  # Stop the test
        
        # Calculate time within current stage
        stage_run_time = run_time - (current_stage_index * self.stage_duration)
        
        # Kill time before stage transition (last 10% of stage duration)
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
        
        logging.info(f"Stage {current_stage_index + 1}/{self.num_stages}: "
                    f"{target_users} users ({stage['users_percentage']*100:.0f}% of max)")
        
        return (target_users, spawn_rate)

class RampUpWebStoreUser(HttpUser):
    """
    User behavior for ramp-up load testing of OpenTelemetry Demo web store
    Realistic user behavior with varied task weights
    """
    wait_time = between(1, 5)  # Slightly longer wait times for ramp-up testing

    def on_start(self):
        """Initialize user session"""
        self.session_id = str(uuid.uuid4())
        self.currency = random.choice(CURRENCIES)

    @task(20)
    def browse_home(self):
        """Visit the home page - most common action"""
        self.client.get("/")

    @task(15)
    def get_products(self):
        """Get product catalog via API"""
        self.client.get("/api/products", params={
            "currencyCode": self.currency
        })

    @task(12)
    def view_product_details(self):
        """View individual product details"""
        product_id = random.choice(PRODUCT_IDS)
        self.client.get(f"/api/products/{product_id}", params={
            "currencyCode": self.currency
        })

    @task(8)
    def view_cart(self):
        """View shopping cart"""
        self.client.get("/api/cart", params={
            "sessionId": self.session_id,
            "currencyCode": self.currency
        })

    @task(6)
    def add_to_cart(self):
        """Add item to cart"""
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 3)
        
        self.client.post("/api/cart", json={
            "userId": self.session_id,
            "item": {
                "productId": product_id,
                "quantity": quantity
            }
        })

    @task(5)
    def get_recommendations(self):
        """Get product recommendations"""
        product_ids = random.sample(PRODUCT_IDS, random.randint(1, 3))
        self.client.get("/api/recommendations", params={
            "productIds": product_ids,
            "sessionId": self.session_id
        })

    @task(3)
    def set_currency(self):
        """Set currency preference"""
        new_currency = random.choice(CURRENCIES)
        self.client.post("/api/currency", json={
            "currencyCode": new_currency
        })
        self.currency = new_currency

    @task(3)
    def get_shipping_quote(self):
        """Get shipping cost estimate"""
        self.client.post("/api/shipping", json={
            "address": {
                "streetAddress": "123 Main St",
                "city": "Test City", 
                "state": "Test State",
                "country": "US",
                "zipCode": "12345"
            },
            "items": [{
                "productId": random.choice(PRODUCT_IDS),
                "quantity": random.randint(1, 2)
            }]
        })

    @task(2)
    def checkout_flow(self):
        """Simulate checkout process - less frequent but important"""
        self.client.post("/api/checkout", json={
            "userId": self.session_id,
            "userCurrency": self.currency,
            "address": {
                "streetAddress": "123 Main St",
                "city": "Test City",
                "state": "Test State", 
                "country": "US",
                "zipCode": "12345"
            },
            "email": "test@example.com",
            "creditCard": {
                "creditCardNumber": "4432-8015-6152-0454",
                "creditCardExpirationMonth": 12,
                "creditCardExpirationYear": 2025,
                "creditCardCvv": 123
            }
        })

    @task(1)
    def empty_cart(self):
        """Empty the shopping cart - least frequent action"""
        self.client.delete("/api/cart", json={
            "userId": self.session_id
        })
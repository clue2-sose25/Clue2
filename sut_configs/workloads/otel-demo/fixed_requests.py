#!/usr/bin/python

# Fixed Requests Load Generator for OpenTelemetry Demo
# Based on the teastore fixed_requests.py pattern
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
import logging
import uuid
import threading
import signal
import os
from locust import HttpUser, task, between, events

# Set up logging
logging.getLogger().setLevel(logging.INFO)

# Configuration
max_requests = int(os.getenv("MAXIMUM_REQUESTS", 1000))
request_count = 0
stopped = False
quitting = False

lock = threading.Lock()

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

# Function to check maximum and quit
def check_maximum_and_quit():
    global request_count
    global stopped
    with lock:
        if request_count >= max_requests:
            stopped = True
            signal.raise_signal(signal.SIGTERM)

# Event listener for request success
@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response,
                       context, exception, start_time, url, **kwargs):
    global request_count
    with lock:
        request_count += 1
    check_maximum_and_quit()

class FixedRequestWebStoreUser(HttpUser):
    """
    Fixed request count user behavior for OpenTelemetry Demo web store
    Stops after reaching the maximum number of requests
    """
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session"""
        self.session_id = str(uuid.uuid4())
        self.currency = random.choice(CURRENCIES)

    @task
    def complete_user_journey(self):
        """
        Complete user journey simulation with request counting
        """
        global stopped
        global request_count

        if stopped:
            self.environment.process_exit_code = 0
            self.environment.runner.stop()
            logging.info(f"Reached task limit {request_count}, quitting")
            return
        
        logging.info(f"Starting user journey {request_count}")
        
        # Browse home page
        self.browse_home()
        
        # Get product catalog
        self.get_products()
        
        # View some product details
        for _ in range(random.randint(1, 3)):
            self.view_product_details()
        
        # Add items to cart (50% chance)
        if random.choice([True, False]):
            for _ in range(random.randint(1, 2)):
                self.add_to_cart()
        
        # View cart
        self.view_cart()
        
        # Get recommendations
        self.get_recommendations()
        
        # Complete purchase (30% chance)
        if random.random() < 0.3:
            self.checkout_flow()
        else:
            # Or empty cart (20% chance)
            if random.random() < 0.2:
                self.empty_cart()
        
        logging.info("Completed user journey.")
        check_maximum_and_quit()

    def browse_home(self):
        """Visit the home page"""
        if stopped:
            return
        self.client.get("/")

    def get_products(self):
        """Get product catalog via API"""
        if stopped:
            return
        self.client.get("/api/products", params={
            "currencyCode": self.currency
        })

    def view_product_details(self):
        """View individual product details"""
        if stopped:
            return
        product_id = random.choice(PRODUCT_IDS)
        self.client.get(f"/api/products/{product_id}", params={
            "currencyCode": self.currency
        })

    def view_cart(self):
        """View shopping cart"""
        if stopped:
            return
        self.client.get("/api/cart", params={
            "sessionId": self.session_id,
            "currencyCode": self.currency
        })

    def add_to_cart(self):
        """Add item to cart"""
        if stopped:
            return
        product_id = random.choice(PRODUCT_IDS)
        quantity = random.randint(1, 3)
        
        self.client.post("/api/cart", json={
            "userId": self.session_id,
            "item": {
                "productId": product_id,
                "quantity": quantity
            }
        })

    def get_recommendations(self):
        """Get product recommendations"""
        if stopped:
            return
        product_ids = random.sample(PRODUCT_IDS, random.randint(1, 3))
        self.client.get("/api/recommendations", params={
            "productIds": product_ids,
            "sessionId": self.session_id
        })

    def set_currency(self):
        """Set currency preference"""
        if stopped:
            return
        new_currency = random.choice(CURRENCIES)
        self.client.post("/api/currency", json={
            "currencyCode": new_currency
        })
        self.currency = new_currency

    def get_shipping_quote(self):
        """Get shipping cost estimate"""
        if stopped:
            return
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

    def checkout_flow(self):
        """Simulate checkout process"""
        if stopped:
            return
        # Place order
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

    def empty_cart(self):
        """Empty the shopping cart"""
        if stopped:
            return
        self.client.delete("/api/cart", json={
            "userId": self.session_id
        })
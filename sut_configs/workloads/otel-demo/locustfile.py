#!/usr/bin/python

# Working OpenTelemetry Demo Load Generator
# Based on actual API structure from the OTS repository
# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random
import logging
import uuid
from locust import HttpUser, task, between

# Set up logging
logging.getLogger().setLevel(logging.ERROR)

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


class WebStoreUser(HttpUser):
    """
    Realistic user behavior for OpenTelemetry Demo web store
    Based on actual Next.js API routes and frontend structure
    """
    wait_time = between(1, 3)

    def on_start(self):
        """Initialize user session"""
        self.session_id = str(uuid.uuid4())
        self.currency = random.choice(CURRENCIES)

    @task(15)
    def browse_home(self):
        """Visit the home page"""
        self.client.get("/")

    @task(12)
    def get_products(self):
        """Get product catalog via API"""
        self.client.get("/api/products", params={
            "currencyCode": self.currency
        })

    @task(8)
    def view_product_details(self):
        """View individual product details"""
        product_id = random.choice(PRODUCT_IDS)
        self.client.get(f"/api/products/{product_id}", params={
            "currencyCode": self.currency
        })

    @task(6)
    def view_cart(self):
        """View shopping cart"""
        self.client.get("/api/cart", params={
            "sessionId": self.session_id,
            "currencyCode": self.currency
        })

    @task(4)
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

    @task(3)
    def get_recommendations(self):
        """Get product recommendations"""
        product_ids = random.sample(PRODUCT_IDS, random.randint(1, 3))
        self.client.get("/api/recommendations", params={
            "productIds": product_ids,
            "sessionId": self.session_id
        })

    @task(2)
    def set_currency(self):
        """Set currency preference"""
        new_currency = random.choice(CURRENCIES)
        self.client.post("/api/currency", json={
            "currencyCode": new_currency
        })
        self.currency = new_currency

    @task(2)
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

    @task(1)
    def checkout_flow(self):
        """Simulate checkout process"""
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

    @task(1)
    def empty_cart(self):
        """Empty the shopping cart"""
        self.client.delete("/api/cart", json={
            "userId": self.session_id
        })

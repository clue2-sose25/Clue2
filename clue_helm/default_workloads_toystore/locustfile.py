#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import random

from locust import HttpUser, task, between

categories = [
    "1",
    "2",
    "3",
]

products = [
    "1",
    "2",
    "3",
]

class WebsiteUser(HttpUser):
    wait_time = between(1, 2)

    @task(1)
    def index(self):
        self.client.get("/")

    @task(10)
    def browse_toy(self):
        self.client.get("/toy/" + random.choice(products))

    @task(3)
    def browse_categories(self):
        self.client.get("/category/" + random.choice(categories))

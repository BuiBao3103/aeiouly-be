
from locust import HttpUser, task, between
import random

class LoadTest(HttpUser):
    wait_time = between(1, 2)
    
    @task
    def get_endpoint(self):
        page = random.randint(1, 10)
        size = random.choice([10, 20, 50])
        
        self.client.get(
            "/api/v1/background-videos/",
            params={"page": page, "size": size},
            headers={"accept": "application/json"}
        )

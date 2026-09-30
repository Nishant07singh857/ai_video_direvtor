from locust import HttpUser, task, between

class RenderUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def render_video(self):
        self.client.post("/api/render", json={"video_id": "test_id", "settings": {}})

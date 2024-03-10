import base64
import re
from datetime import datetime

from locust import HttpUser, task

username = 'birdnet'
password = 'lepotato'


class WorldUser(HttpUser):
    @task(3)
    def hello_world(self):
        self.client.get("/")

    @task(2)
    def today_recordings(self):
        self.client.get(f"/views.php?view=Recordings&bydate={datetime.now().strftime('%Y-%m-%d')}")

    @task
    def today(self):
        self.client.get("/views.php?view=Todays+Detections")
        self.client.get("/views.php?view=Species+Stats")
        self.client.get("/views.php?view=Streamlit")
        self.client.get("/views.php?view=Spectrogram")
        self.client.get("/views.php?view=Daily+Charts")
        self.client.get("/views.php?view=Recordings&byspecies=byspecies")
        self.client.get("/views.php?view=Recordings&bydate=bydate")
        self.client.get("/views.php?view=View+Log")
        self.client.get("/views.php?view=Weekly+Report")


class AuthenticatedUser(WorldUser):
    def on_start(self):
        credentials = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('ISO-8859-1')
        self.client.headers = {
            'Authorization': f'Basic {credentials}',
        }

    @task
    def spectrogram(self):
        self.client.get("/views.php?view=Spectrogram")


class BadUser(HttpUser):
    @task
    def dummy(self):
        pass

    @task
    def stream(self):
        self.client.get("/?stream=play")

    @task
    def tools(self):
        self.client.get("/scripts/adminer.php")
        self.client.get("/views.php?view=Webterm")
        self.client.get("/views.php?view=System+Controls")
        self.client.get("/views.php?view=Services")
        self.client.get("/views.php?view=Tools")
        self.client.get("/views.php?view=Settings")
        self.client.get("/views.php?view=Advanced")
        self.client.get("/views.php?view=Included")
        self.client.get("/views.php?view=Excluded")

    @task
    def filemanager(self):
        # caddy protected
        self.client.get("/scripts/filemanager/filemanager.php")
        # caddy protected
        # iframe
        with self.client.get("/views.php?view=File", catch_response=True) as response:
            if response.status_code < 400:
                iframe = re.search('<iframe src=[\"\']?([a-zA-Z0-9./]+)', response.text).group(1)
                response2 = self.client.get(f"/{iframe}")
                if response2.status_code >= 400:
                    response.failure(response2.status_code)

    @task
    def sysinfo(self):
        # caddy protected
        self.client.get("/phpsysinfo/index.php")
        # caddy protected
        # iframe
        with self.client.get("/views.php?view=System+Info", catch_response=True) as response:
            if response.status_code < 400:
                iframe = re.search('<iframe src=[\"\']?([a-zA-Z0-9./]+)', response.text).group(1)
                response2 = self.client.get(f"/{iframe}")
                if response2.status_code >= 400:
                    response.failure(response2.status_code)


class Admin(BadUser):
    def on_start(self):
        credentials = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('ISO-8859-1')
        self.client.headers = {
            'Authorization': f'Basic {credentials}',
        }

    @task
    def spectrogram(self):
        self.client.get("/views.php?view=Spectrogram")

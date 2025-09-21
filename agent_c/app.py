from fastapi import FastAPI
import requests

app = FastAPI()

AGENT_S_URL = "http://agent_s:9000/forward"

@app.get("/send")
def send_message():
    # No certs here (external agent)
    r = requests.post(AGENT_S_URL, json={"msg": "hello from C"})
    return {"response": r.json()}

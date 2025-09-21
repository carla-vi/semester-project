from fastapi import FastAPI, Request
import requests

app = FastAPI()
AGENT_B_URL = "https://agent_b:8001/ask"

@app.post("/forward")
async def forward(req: Request):
    data = await req.json()

    # Simple: log + forward with enterprise trust
    r = requests.post(
        AGENT_B_URL,
        json=data,
        cert=("/certs/agentS.crt", "/certs/agentS.key"),
        verify="/certs/rootCA.crt"
    )
    return {"forwarded": True, "b_response": r.json()}

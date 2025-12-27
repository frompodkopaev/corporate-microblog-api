from typing import Dict

from fastapi import FastAPI

app = FastAPI()


@app.get("/hello-world")
async def hello_world() -> Dict[str, str]:
    return {"message": "Hello world!"}
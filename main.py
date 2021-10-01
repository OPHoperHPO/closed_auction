import uvicorn as uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.post(path="/api/v1/create_auction")
def create():
    pass


@app.post(path="/api/v1/bid")
def bid():
    pass


@app.post(path="/api/v1/verify")
def verify():
    pass


@app.post(path="/api/v1/commit")
def commit():
    pass


@app.get("/api/v1/list_all_auctions")
def list_all():
    pass


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)

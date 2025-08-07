from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    print("Simple server root endpoint accessed")
    return {"message": "Simple server is running"}

@app.get("/test")
def test():
    print("Simple server test endpoint accessed")
    return {"message": "Simple server test successful"}

if __name__ == "__main__":
    import uvicorn
    print("Starting simple server on localhost:8000")
    uvicorn.run(app, host="localhost", port=8000)
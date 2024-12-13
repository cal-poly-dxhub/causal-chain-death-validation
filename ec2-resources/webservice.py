from fastapi import FastAPI
from testtxt import checkSimilar

app = FastAPI()

@app.get("/")
def root():
    return {"Mortem":"Matters"}

@app.get("/embeddings/{inputCondition}")
def getNeighbors(inputCondition: str):
    return checkSimilar(inputCondition)

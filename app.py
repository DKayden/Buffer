from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from buffer import modbus_client
from config import ACTION_ADDRESS, RECEIVE_ADDRESS, TRANSFER_ADDRESS, GIVE_ADDRESS

app = FastAPI(
    title="Buffer API",
    openapi_url="/openapi.json",
    docs_url="/docs",
    description="Buffer API documentation"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

@app.get("/buffer")
async def buffer(type: str):
    if type == "flip":
        modbus_client.write_register(ACTION_ADDRESS, 2)
        return {"message": "Buffer đã nhận lệnh lật!"}
    elif type == "circular":
        modbus_client.write_register(ACTION_ADDRESS, 1)
        return {"message": "Buffer đã nhận lệnh xoay."}
    else:
        return {"error": "Loại hành động không hợp lệ."}
    
@app.get("/getmagazine")
async def getmagazine():
    modbus_client.write_register(TRANSFER_ADDRESS, 1)
    return {"message": "Băng tải Buffer quay để nhận magazine"}

@app.get("/confirmreceive")
async def confirmreceive():
    return modbus_client.read_input_register(GIVE_ADDRESS, 1)[0] == 1

@app.get("/receivemagazine")
async def receivemagazine(type: str):
    if type == "confirm":
        modbus_client.write_register(RECEIVE_ADDRESS, 0)
        return {"message": "AMR xác nhận đã tới lấy."}
    elif type == "done":
        modbus_client.write_register(RECEIVE_ADDRESS, 1)
        return {"message": "AMR xác nhận đã hoàn thành lấy."}
    
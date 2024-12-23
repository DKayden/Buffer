from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from modbus_client import ModbusClient
from config import ACTION_ADDRESS, RECEIVE_ADDRESS, MODBUS_HOST, MODBUS_PORT, TRANSFER_ADDRESS, MODBUS_TYPE
import uvicorn
from process_handle import ProccessHandler

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
        client_module.write_register(ACTION_ADDRESS, 2)
        return {"message": "Buffer đã nhận lệnh lật!"}
    elif type == "circular":
        client_module.write_register(ACTION_ADDRESS, 1)
        return {"message": "Buffer đã nhận lệnh xoay."}
    else:
        return {"error": "Loại hành động không hợp lệ."}
    
@app.get("/getmagazine")
async def getmagazine():
    client_module.write_register(TRANSFER_ADDRESS, 1)
    return {"message": "Băng tải Buffer quay để nhận magazine"}

@app.get("/receivemagazine")
async def receivemagazine(type: str):
    if type == "confirm":
        client_module.write_register(RECEIVE_ADDRESS, 0)
        return {"message": "AMR xác nhận đã tới lấy."}
    elif type == "done":
        client_module.write_register(RECEIVE_ADDRESS, 1)
        return {"message": "AMR xác nhận đã hoàn thành lấy."}
    
@app.get("/process")
async def process():
    handler = ProccessHandler()
    return await handler.handle_magazine_process()
    
if __name__ == "__main__":
    client_module = ModbusClient(MODBUS_HOST, MODBUS_PORT, MODBUS_TYPE)
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="debug")
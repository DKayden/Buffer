from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from buffer import modbus_client
from config import ACTION_ADDRESS, TRANSFER_ADDRESS, GIVE_ADDRESS, TURN_ADDRESS
from socket_server import SocketServer
from pydantic import BaseModel
from process_handle import ProccessHandler
import threading
from test import pause_event, cancel_event

socket_server = SocketServer()
process_handler = ProccessHandler()

app = FastAPI(
    title="Buffer API",
    openapi_url="/openapi.json",
    docs_url="/docs",
    description="Buffer API documentation",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Mission(BaseModel):
    floor: int
    line: str
    machine_type: str


@app.get("/buffer")
async def buffer(type: str):
    if type == "flip":
        modbus_client.write_register(ACTION_ADDRESS, 1)
        return {"message": "Buffer đã nhận lệnh lật!"}
    elif type == "circular":
        modbus_client.write_register(ACTION_ADDRESS, 2)
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
        modbus_client.write_register(GIVE_ADDRESS, 1)
        return {"message": "AMR xác nhận đã tới lấy."}
    elif type == "done":
        modbus_client.write_register(GIVE_ADDRESS, 0)
        return {"message": "AMR xác nhận đã hoàn thành lấy."}


@app.post("/turn")
async def turn(direction: str):
    if direction == "clockwise":
        modbus_client.write_register(TURN_ADDRESS, 0)
        return {"message": "Buffer đã nhận lệnh quay thuận."}
    elif direction == "counterclockwise":
        modbus_client.write_register(TURN_ADDRESS, 1)
        return {"message": "Buffer đã nhận lệnh quay nghịch."}
    
@app.get("/current_mission", response_model=Mission | None)
async def get_current_mission():
    missions = socket_server.get_mission_data()
    if missions:
        return missions[0]
    return {"message": "Không có nhiệm vụ hiện tại."}

@app.post("/mission_control")
async def mission_control(type: str):
    if type not in ["pause", "resume", "cancel"]:
        return {"error": "Giá trị type không hợp lệ. Chỉ chấp nhận: pause, resume, cancel."}
    try:
        if type == "pause":
            pause_event.set()
        elif type == "resume":
            pause_event.clear()
        elif type == "cancel":
            cancel_event.set()
        process_handler.control_navigate_action(type)
        return {"message": f"Đã gửi lệnh {type} thành công!"}
    except Exception as e:
        return {"error": str(e)}
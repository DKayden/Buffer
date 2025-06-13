from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from buffer import modbus_client
from config import ACTION_ADDRESS, TRANSFER_ADDRESS, GIVE_ADDRESS, TURN_ADDRESS
from process_handle import ProccessHandler
import state
import re

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


@app.post("/type")
async def mission_control(data: dict):
    if data["type"] not in ["pause", "resume", "cancel"]:
        return {
            "error": "Giá trị type không hợp lệ. Chỉ chấp nhận: pause, resume, cancel."
        }
    try:
        if data["type"] == "pause":
            state.pause_event.set()
        elif data["type"] == "resume":
            state.pause_event.clear()
        elif data["type"] == "cancel":
            state.cancel_event.set()
        process_handler.control_navigate_action(data["type"])
        return {"message": f"Đã gửi lệnh {data['type']} thành công!"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/magazine_status")
async def get_magazine_status():
    return {"magazine_status": state.magazine_status}


@app.get("/call_status")
async def get_call_status():
    return state.call_status


@app.get("/robot_status")
async def get_robot_status():
    return state.robot_status


@app.get("/status")
async def robot_status():
    result = process_handler.read_robot_status()
    return result


@app.post("/line_auto")
async def add_line_auto(data: dict):
    process_handler.add_line_auto(data["line"])
    return {"message": state.line_auto_web}


@app.post("/line_auto_web/remove")
async def remove_line_auto(line: str):
    process_handler.remove_line_auto(line)
    return {"message": "Đã xóa dòng tự động."}


@app.post("/mode")
async def robot_mode(data: dict):
    state.mode = data["mode"]
    return {"message": "Đã thay đổi chế độ."}


@app.post("/run")
async def run_manual(data: dict):  # {"line": "line26", type: "unload", "floor": 1}
    mission_item = {
        "floor": data["floor"],
        "line": re.sub(r"([a-zA-Z])(\d)", r"\1 \2", data["line"]),
        "machine_type": data["type"],
    }
    process_handler.create_mission(mission_item)
    return {"message": data}

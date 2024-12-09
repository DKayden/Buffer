import requests
import asyncio
from buffer import (allow_transfer_magazine, confirm_transfer_magazine
                    , confirm_receive_magazine, buffer_action, robot_wanna_receive_magazine
                    , robot_confirm_receive_magazine)
from modbus_client import ModbusClient
from config import (PI_HOST, PI_PORT, ROBOT_HOST, ROBOT_PORT, BUFFER_HOST, BUFFER_PORT
                    , MODBUS_HOST, MODBUS_PORT, MODBUS_TYPE)

modbus_client = ModbusClient(host=MODBUS_HOST, port=MODBUS_PORT, type=MODBUS_TYPE)

class ProccessHandler():
    def __init__(self):
        self.pi_url = f"http://{PI_HOST}:{PI_PORT}"
        self.robot_url = f"http://{ROBOT_HOST}:{ROBOT_PORT}"

    async def handle_magazine_process(self):
        try:
            # Nhận thông tin từ Pi
            data_pi = requests.get(f"{self.pi_url}/get_action")
            action_type = data_pi.json()["type"]
            pick_up = data_pi.json()["pickup"]
            drop_off = data_pi.json()["dropoff"]
            print(f"Action type: {action_type}, pickup: {pick_up}, dropoff: {drop_off}")

            # Điều khiển robot tới vị trí lấy magazine
            

            # Quay băng tải để lấy magazine từ máy


            # Điều khiển robot tới vị trí buffer


            # Chờ xác nhận buffer sẵn sàng
            while not allow_transfer_magazine():
                print("Buffer chưa sẵn sàng!!!")
                await asyncio.sleep(1)
            print("Buffer đã sẵn sàng!!!!")

            # Robot quay băng tải để truyền magazine vào buffer


            # Buffer quay băng tải để nhận magazine
            

            while not confirm_transfer_magazine():
                print("Buffer chưa hoàn thành nhận magazine!!!")
                await asyncio.sleep(1)
            print("Buffer đã nhận magazine!!!")

            # Thực hiện hành động theo yêu cầu
            buffer_action(action=action_type)
            print("Buffer đã bắt đầu thao tác")

            # Chờ buffer xử lý xong và sẵn sàng để trả magazine
            while not confirm_receive_magazine():
                print("Buffer chưa hoàn thành xử lý!!!")
                await asyncio.sleep(1)
            print("Buffer đã hoàn thành xử lý, robot có thể đến lấy!!!")

            # Robot xác nhận muốn lấy magazine
            robot_wanna_receive_magazine()

            # Buffer quay băng tải để trả magazine


            # Robot quay băng tải để lấy magazine


            # Robot xác nhận đã lấy magazine xong
            robot_confirm_receive_magazine()

            # Điều khiển robot tới vị trí trả magazine


            return {"message": "Quá trình xử lý hoàn tất"}


        except Exception as e:
            return {"error": f"Lỗi trong quá trình xử lý: {str(e)}"}
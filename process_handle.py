import requests
import asyncio
from buffer import (allow_transfer_magazine, confirm_transfer_magazine
                    , confirm_receive_magazine, buffer_action, robot_wanna_receive_magazine
                    , robot_confirm_receive_magazine)
from modbus_client import ModbusClient
from config import (PI_HOST, PI_PORT, ROBOT_HOST, ROBOT_PORT, MODBUS_HOST, MODBUS_PORT, MODBUS_TYPE, BUFFER_LOCATION)

modbus_client = ModbusClient(host=MODBUS_HOST, port=MODBUS_PORT, type=MODBUS_TYPE)

class ProccessHandler():
    def __init__(self):
        self.pi_url = f"http://{PI_HOST}:{PI_PORT}"
        self.robot_url = f"http://{ROBOT_HOST}:{ROBOT_PORT}"
        self.mission = []

    async def control_robot_to_location(self, location):
        try:
            response = requests.post(f"{self.robot_url}/navigation", json={
                "position": location,
            })
            if response.status_code != 200:
                raise requests.exceptions.RequestException(f"Lỗi đường truyền khi gửi thông tin đến robot. Trạng thái: {response.status_code}")
            print(f"Robot di chuyển tới: {location}")
            
            # Đợi robot xác nhận đã tới điểm
            while True:
                status = requests.get(f"{self.robot_url}/status").json()
                if status.get("status") == "completed":
                    break
                await asyncio.sleep(3)
            print(f"Robot đã tới {location}")
            
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển di chuyển của robot: {str(e)}")
            raise requests.exceptions.RequestException("Thất bại khi điều khiển di chuyển của robot") from e
        
    async def get_mission_from_pi(self):
        """
        Hàm này lấy thông tin nhiệm vụ và thêm vào danh sách nhiệm vụ.

        """
        try:
            # Lấy thông tin nhiệm vụ từ Pi
            response = requests.get(f"{self.pi_url}/mission")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(f"Lỗi khi lấy dữ liệu từ Pi. Mã trạng thái: {response.status_code}")
            mission_info = response.json()
            print(f"Thông tin nhiệm vụ đã lấy từ Pi: {mission_info}")

            # Thêm nhiệm vụ vào danh sách
            self.mission.append(mission_info)
            print(f"Nhiệm vụ đã thêm vào danh sách: {self.mission}")

        except requests.exceptions.RequestException as e:
            print(f"Xảy ra lỗi lấy thông tin nhiệm vụ từ Pi: {str(e)}")
            raise requests.exceptions.RequestException("Lỗi lấy thông tin nhiệm vụ từ Pi") from e

    async def handle_magazine_process(self):
        while self.mission:
            try:
                action_type = self.mission["type"]
                location = self.mission["location"]
                destination = self.mission["destination"]
                print(f"Action type: {action_type}, pickup: {location}, dropoff: {destination}")

                # Điều khiển robot tới vị trí lấy magazine
                # await self.control_robot_to_location(location)

                # Robot quay băng tải để lấy magazine từ máy
                print("Robot quay băng tải để nhận magazine từ máy")

                # Gửi nhiệm vụ theo yêu cầu cho Buffer
                buffer_action(action=action_type)

                # Điều khiển robot tới vị trí buffer
                # await self.control_robot_to_location(BUFFER_LOCATION)

                # Buffer quay băng tải để nhận magazine
                allow_transfer_magazine()
                await asyncio.sleep(3)

                # Robot quay băng tải để truyền magazine vào buffer
                print("Robot quay băng tải để truyền magazine vào Buffer")

                # Chờ buffer xác nhận đã nhận xong magazine
                while not confirm_transfer_magazine():
                    print("Buffer chưa hoàn thành nhận magazine!!!")
                    await asyncio.sleep(3)
                print("Buffer đã nhận magazine!!!")

                # Chờ buffer xử lý xong và sẵn sàng để trả magazine
                while not confirm_receive_magazine():
                    print("Buffer chưa hoàn thành xử lý!!!")
                    await asyncio.sleep(3)
                print("Buffer đã hoàn thành xử lý, robot có thể đến lấy!!!")

                # Robot xác nhận muốn lấy magazine
                robot_wanna_receive_magazine()
                await asyncio.sleep(3)

                # Robot quay băng tải để lấy magazine
                print("Robot quay băng tải để nhận magazine")

                # Robot xác nhận đã lấy magazine xong
                robot_confirm_receive_magazine()

                # Điều khiển robot tới vị trí trả magazine
                # await self.control_robot_to_location(destination)

                # Robot quay băng tải để trả hàng cho máy
                print("Robot quay băng tải để truyền magazine cho máy")

                return {"message": "Quá trình xử lý hoàn tất"}
            except requests.exceptions.RequestException as e:
                return {"error": f"Lỗi trong quá trình xử lý: {str(e)}"}
import requests
import asyncio
from buffer import (allow_transfer_magazine, confirm_transfer_magazine
                    , confirm_receive_magazine, buffer_action, robot_wanna_receive_magazine
                    , robot_confirm_receive_magazine)
from modbus_client import ModbusClient
from config import (ROBOT_HOST, ROBOT_PORT, MODBUS_HOST, MODBUS_PORT, MODBUS_TYPE, BUFFER_LOCATION,
                    MAP_LINE, BUFFER_ACTION)
from mongodb import BufferDatabase
from socket_server import SocketServer
import logging

modbus_client = ModbusClient(host=MODBUS_HOST, port=MODBUS_PORT, type=MODBUS_TYPE)

buffer_db = BufferDatabase()

CW = []

# Khởi tạo socket server
socket_server = SocketServer()


class ProccessHandler():
    def __init__(self):
        self.robot_url = f"http://{ROBOT_HOST}:{ROBOT_PORT}"
        self.mission = []

    async def control_robot_to_location(self, location):
        try:
            response = requests.post(f"{self.robot_url}/navigation", json={
                "data": location,
            })
            if response.status_code != 200:
                raise requests.exceptions.RequestException(f"Lỗi đường truyền khi gửi thông tin đến robot. Trạng thái: {response.status_code}")
            print(f"Robot di chuyển tới: {location}")
            
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển di chuyển của robot: {str(e)}")
            raise requests.exceptions.RequestException("Thất bại khi điều khiển di chuyển của robot") from e
        

    async def check_location_robot(self, location):
    # Robot xác nhận đã tới điểm
        while True:
            status = requests.get(f"{self.robot_url}/checklocation", json={
                "data": location,
            })
            if status:
                break
            await asyncio.sleep(3)
        print(f"Robot đã tới {location}")

    async def control_robot_conveyor(self, direction):
        """
            Hàm này điều khiển quay băng tải của robot theo hướng đã cho.

        Args:
            direction (str): Hướng của băng tải, có thể là "stop" hoặc "cw" hoặc 'ccw'.
        """
        try:
            if direction not in ["stop", "cw", "ccw"]:
                raise ValueError("Hướng băng tải phải là 'stop' hoặc 'cw' hoặc 'ccw'.")
            response = requests.post(f"{self.robot_url}/conveyor", json={
                "data": direction,
            })
            if response.status_code != 200:
                raise requests.exceptions.RequestException(f"Lỗi đường truyền khi điều khiển băng tải của robot. Trạng thái: {response.status_code}")
            print("Băng tải của robot đã được điều khiển")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException("Thất bại khi điều khiển băng tải của robot") from e
        
    async def check_conveyor_robot(self, direction):
        """
        Hàm này kiểm tra trạng thái của băng tải của robot.

        Returns:
            bool.
        """
        try:
            response = requests.get(f"{self.robot_url}/conveyor?type={direction}")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(f"Lỗi đường truyền khi kiểm tra trạng thái băng tải của robot. Mã trạng thái: {response.status_code}")
            return response
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình kiểm tra trạng thái băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException("Thất bại khi kiểm tra trạng thái băng tải của robot") from e
    
    async def direction_conveyor(self, location):
        return 'cw' if location in CW else 'ccw'
    
    async def control_robot_stopper(self, action):
        """
            Hàm này điều khiển cửa băng tải của robot.
        Args:
            action (str): Hành động cần thực hiện, có thể là "close" hoặc "open".
        """
        try:
            if action not in ["open", "close"]:
                raise ValueError("Hành động đóng cửa phải là 'open' hoặc 'close'.")
            response = requests.post(f"{self.robot_url}/stopper", json={
                "data": action,
            })
            if response.status_code!= 200:
                raise requests.exceptions.RequestException(f"Lỗi đường truyền khi điều khiển cửa băng tải của robot. Mã trạng thái: {response.status_code}")
            print("Cửa băng tải của robot đã được điều khiển thành công")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển cửa băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException("Thất bại khi điều khiển cửa băng tải của robot") from e
    
    async def get_data_from_socket_server(self):
        """
        Hàm này lấy thông tin dữ liệu từ socket server
        """
        try:
            # Lấy dữ liệu từ socket server
            data = socket_server.get_received_data()
            if not data:
                logging.warning("Không có dữ liệu từ socket server")
                return
            return data
        except Exception as e:
            print(f"Lỗi trong quá trình lấy dữ liệu từ socket server: {str(e)}")
            raise e from None
                

    async def create_mission(self):
        """
        Hàm này lấy thông tin nhiệm vụ từ socket server và thêm vào danh sách nhiệm vụ.
        """
        try:
            data = self.get_data_from_socket_server()
            # Chuyển đổi dữ liệu string thành dict
            try:
                mission_data = eval(data)
            except (SyntaxError, ValueError, NameError) as e:
                raise ValueError(f"Dữ liệu nhận được không đúng định dạng: {str(e)}")
            
            # Kiểm tra và xử lý dữ liệu
            line = mission_data.get('line')
            machine_type = mission_data.get('machine_type')
            floor = mission_data.get('floor')
                
            if not line or not machine_type or not floor:
                raise ValueError("Thiếu thông tin line hoặc machine_type hoặc floor trong dữ liệu nhận được")
                
            logging.info(f"Đã nhận nhiệm vụ: line={line}, machine_type={machine_type}")
            
            # Xử lý thông tin nhiệm vụ
            if line in MAP_LINE:
                station = MAP_LINE[line]
                pick_up, destination = (station[0], station[1]) if machine_type == "loader" else (station[1], station[0])
                    
                logging.info(f"Tạo nhiệm vụ từ {pick_up} đến {destination}")
                    
                # Thêm nhiệm vụ mới
                self.mission.append({
                    "pick_up": pick_up,
                    "destination": destination,
                    "floor": floor
                })
                logging.info(f"Đã thêm nhiệm vụ mới: {self.mission[-1]}")
            else:
                raise ValueError(f"Không tìm thấy thông tin cho line: {line}")
                
        except Exception as e:
            logging.error(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")
            raise
    
    async def send_message_to_machine(self, location):
        """
        Hàm này gửi thông tin muốn nhận magazine tới máy
        """
        try:
            # Tìm máy để nhận magazine
            target_client = next((client for client, info in socket_server.client_info.items()
                                  if info['location'] == location), None)
            if target_client:
                socket_server.broadcast_message("request_magazine", target_client)
                print(f"Đã gửi thông tin muốn nhận magazine tới máy {location}")
            else:
                raise ValueError(f"Không tìm thấy máy để nhận magazine tại vị trí {location}")
        except Exception as e:
            logging.error(f"Lỗi trong quá trình gửi thông tin muốn nhận magazine: {str(e)}")
            raise

    async def handle_magazine_process(self):
        while self.mission:
            try:
                # Trích xuất thông tin từ danh sách nhiệm vụ
                pick_up = self.mission[0]["pick_up"]
                destination = self.mission[0]["destination"]
                print(f"Pickup: {pick_up}, dropoff: {destination}")
                dir_pick_up = self.direction_conveyor(pick_up)
                dir_destination = self.direction_conveyor(destination)
                
                # Điều khiển robot tới vị trí lấy magazine
                await self.control_robot_to_location(pick_up)

                # Kiểm tra xem robot đã tới vị trí lấy magazine
                await self.check_location_robot(pick_up)

                # Robot mở stopper
                self.control_robot_stopper("open")

                # Robot quay băng tải để lấy magazine từ máy
                await self.control_robot_conveyor(dir_pick_up)
                print("Robot quay băng tải để nhận magazine từ máy")

                # Gửi thông tin muốn nhận magazine
                self.send_message_to_machine(pick_up)

                # Kiểm tra xem robot đã nhận magazine từ máy
                while self.check_conveyor_robot(dir_pick_up):
                    print("Robot chưa nhận magazine từ máy!!!")
                    await asyncio.sleep(3)
                print("Robot đã nhận magazine từ máy!!!")

                # Robot đóng stopper
                self.control_robot_stopper("close")

                # Robot dừng băng tải
                await self.control_robot_conveyor("stop")

                # Gửi nhiệm vụ theo yêu cầu cho Buffer
                buffer_action(action=BUFFER_ACTION)

                # Điều khiển robot tới vị trí buffer
                await self.control_robot_to_location(BUFFER_LOCATION)

                # Kiểm tra xem robot đã tới vị trí buffer
                while not self.check_location_robot(BUFFER_LOCATION):
                    print("Robot chưa tới vị trí buffer!!!")
                    await asyncio.sleep(3)
                print("Robot đã tới vị trí buffer!!!")
                
                # Buffer quay băng tải để nhận magazine
                allow_transfer_magazine()
                await asyncio.sleep(3)

                # Robot mở stopper
                self.control_robot_stopper("open")

                # Robot quay băng tải để truyền magazine vào buffer
                await self.control_robot_conveyor("cw")
                print("Robot quay băng tải để truyền magazine vào Buffer")

                # Chờ buffer xác nhận đã nhận xong magazine
                while not confirm_transfer_magazine():
                    print("Buffer chưa hoàn thành nhận magazine!!!")
                    await asyncio.sleep(3)
                print("Buffer đã nhận magazine!!!")

                # Robot dừng băng tải
                await self.control_robot_conveyor("stop")

                # Chờ buffer xử lý xong và sẵn sàng để trả magazine
                while not confirm_receive_magazine():
                    print("Buffer chưa hoàn thành xử lý!!!")
                    await asyncio.sleep(3)
                print("Buffer đã hoàn thành xử lý, robot có thể đến lấy!!!")

                # Robot quay băng tải để lấy magazine
                await self.control_robot_conveyor("ccw")
                print("Robot quay băng tải để nhận magazine")

                # Robot xác nhận muốn lấy magazine
                robot_wanna_receive_magazine()
                await asyncio.sleep(3)

                # Kiểm tra xem robot đã nhận magazine từ buffer
                while self.check_conveyor_robot("ccw"):
                    print("Robot chưa nhận magazine từ Buffer!!!")
                    await asyncio.sleep(3)
                print("Robot đã nhận magazine từ Buffer!!!")

                # Robot đóng stopper
                self.control_robot_stopper("close")

                # Robot xác nhận đã lấy magazine xong
                robot_confirm_receive_magazine()

                # Điều khiển robot tới vị trí trả magazine
                await self.control_robot_to_location(destination)

                # Kiểm tra xem robot đã tới vị trí trả magazine
                await self.check_location_robot(destination)

                # Robot mở stopper
                self.control_robot_stopper("open")

                # Gửi thông tin trả magazine cho máy
                self.send_message_to_machine(destination)

                # Robot quay băng tải để trả hàng cho máy
                await self.control_robot_conveyor(dir_destination)
                print("Robot quay băng tải để truyền magazine cho máy")

                # Máy xác nhận đã nhận magazine

                # Robot dừng băng tải
                await self.control_robot_conveyor("stop")

                # Robot đóng stopper
                self.control_robot_stopper("close")

                # Xóa nhiệm vụ đã hoàn thành
                self.mission.pop(0)
                print(f"Nhiệm vụ đã hoàn thành: {self.mission}")

                return {"message": "Quá trình xử lý hoàn tất"}
            except requests.exceptions.RequestException as e:
                return {"error": f"Lỗi trong quá trình xử lý: {str(e)}"}
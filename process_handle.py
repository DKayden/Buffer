import requests
import asyncio
from buffer import (
    allow_transfer_magazine,
    confirm_transfer_magazine,
    confirm_receive_magazine,
    buffer_action,
    robot_wanna_receive_magazine,
    robot_confirm_receive_magazine,
)
from config import (
    ROBOT_HOST,
    ROBOT_PORT,
    MODBUS_HOST,
    MODBUS_PORT,
    MODBUS_TYPE,
    BUFFER_LOCATION,
    MAP_LINE,
    BUFFER_ACTION,
    HEIGHT_LINE_25,
)
from mongodb import BufferDatabase
from socket_server import SocketServer
import logging
from collections import deque
import json


# buffer_db = BufferDatabase()

CW = []

# Khởi tạo socket server
socket_server = SocketServer()


class ProccessHandler:
    def __init__(self):
        self.robot_url = f"http://{ROBOT_HOST}:{ROBOT_PORT}"
        self.mission = deque()

    def control_robot_to_location(self, location):
        try:
            response = requests.post(
                f"{self.robot_url}/navigation",
                json={
                    "id": location,
                },
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi gửi thông tin đến robot. Trạng thái: {response.status_code}"
                )
            print(f"Robot di chuyển tới: {location}")

        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển di chuyển của robot: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại khi điều khiển di chuyển của robot"
            ) from e

    def check_location_robot(self, location: str):
        # Robot xác nhận đã tới điểm
        flag = requests.get(
            f"{self.robot_url}/checklocation",
            json={
                "location": location,
            },
        )
        print(f"Cờ kiểm tra vị trí robot: {flag}")
        asyncio.sleep(3)

    def control_robot_conveyor(self, direction):
        """
            Hàm này điều khiển quay băng tải của robot theo hướng đã cho.

        Args:
            direction (str): Hướng của băng tải, có thể là "stop" hoặc "cw" hoặc 'ccw'.
        """
        try:
            if direction not in ["stop", "cw", "ccw"]:
                raise ValueError("Hướng băng tải phải là 'stop' hoặc 'cw' hoặc 'ccw'.")
            response = requests.post(
                f"{self.robot_url}/conveyor",
                json={
                    "type": direction,
                },
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển băng tải của robot. Trạng thái: {response.status_code}"
                )
            print("Băng tải của robot đã được điều khiển")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại khi điều khiển băng tải của robot"
            ) from e

    def check_conveyor_robot(self, direction):
        """
        Hàm này kiểm tra trạng thái của băng tải của robot.

        Returns:
            bool.
        """
        try:
            response = requests.get(f"{self.robot_url}/conveyor?type={direction}")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi kiểm tra trạng thái băng tải của robot. Mã trạng thái: {response.status_code}"
                )
            return response
        except requests.exceptions.RequestException as e:
            print(
                f"Lỗi trong quá trình kiểm tra trạng thái băng tải của robot: {str(e)}"
            )
            raise requests.exceptions.RequestException(
                "Thất bại khi kiểm tra trạng thái băng tải của robot"
            ) from e

    def direction_conveyor(self, location):
        return "cw" if location in CW else "ccw"

    def control_robot_stopper(self, action, status):
        """
            Hàm này điều khiển cửa băng tải của robot.
        Args:
            action (str): Hành động cần thực hiện, có thể là "close" hoặc "open".
        """
        try:
            if status not in ["open", "close"]:
                raise ValueError("Hành động đóng cửa phải là 'open' hoặc 'close'.")
            response = requests.post(
                f"{self.robot_url}/stopper",
                json={"action": action, "status": status},
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển cửa băng tải của robot. Mã trạng thái: {response.status_code}"
                )
            print("Cửa băng tải của robot đã được điều khiển thành công")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển cửa băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại khi điều khiển cửa băng tải của robot"
            ) from e

    def control_folk_conveyor(self, height):
        """
        Hàm này điều khiển nâng băng tải của robot.
        """
        try:
            response = requests.post(
                f"{self.robot_url}/lift",
                json={
                    "height": height,
                },
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển nâng băng tải của robot. Mã trạng thái: {response.status_code}"
                )
            print("Nâng băng tải của robot đã được điều khiển thành công")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển nâng băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại khi điều khiển nâng băng tải của robot"
            ) from e

    def get_data_from_socket_server(self):
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

    def is_duplicate_mission(self, new_mission):
        """
        Hàm này kiểm tra xem nhiệm vụ mới có trùng với nhiệm vụ đã đăng ký hay không.
        """
        for mission in self.mission:
            if (
                mission["pick_up"] == new_mission["pick_up"]
                and mission["destination"] == new_mission["destination"]
                and mission["floor"] == new_mission["floor"]
                and mission["line"] == new_mission["line"]
                and mission["machine_type"] == new_mission["machine_type"]
            ):
                return True
        return False

    def _validate_mission_data(self, mission_data):
        """Kiểm tra tính hợp lệ của dữ liệu nhiệm vụ"""
        line = mission_data.get("line")
        machine_type = mission_data.get("machine_type")
        floor = mission_data.get("floor")

        if not line or not machine_type or not floor:
            raise ValueError(
                "Thiếu thông tin line hoặc machine_type hoặc floor trong dữ liệu nhận được"
            )

        return line, machine_type, floor

    def _create_mission_from_data(self, line, machine_type, floor):
        """Tạo nhiệm vụ từ dữ liệu đã xác thực"""
        if line not in MAP_LINE:
            raise ValueError(f"Không tìm thấy thông tin cho line: {line}")

        station = MAP_LINE[line]
        pick_up, destination = (
            (station[0], station[1])
            if machine_type == "loader"
            else (station[1], station[0])
        )
        logging.info(f"Tạo nhiệm vụ từ {pick_up} đến {destination}")

        # Xử lý tạo nhiệm vụ nếu có thông tin tầng
        for i in floor:
            if i != 0:
                new_mission = {
                    "pick_up": pick_up,
                    "destination": destination,
                    "floor": i,
                    "line": line,
                    "machine_type": machine_type,
                }
                if not self.is_duplicate_mission(new_mission):
                    self.mission.append(new_mission)
                    logging.info(f"Đã thêm nhiệm vụ mới: {new_mission}")
                else:
                    raise ValueError("Nhiệm vụ này đã tồn tại trong danh sách chờ")

    def create_mission(self):
        """Hàm này lấy thông tin nhiệm vụ từ socket server và thêm vào danh sách nhiệm vụ."""
        try:
            data = self.get_data_from_socket_server()
            try:
                mission_data = eval(data)
            except (SyntaxError, ValueError, NameError) as e:
                raise ValueError(f"Dữ liệu nhận được không đúng định dạng: {str(e)}")

            line, machine_type, floor = self._validate_mission_data(mission_data)
            self._create_mission_from_data(line, machine_type, floor)

        except Exception as e:
            logging.error(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")
            raise

    def request_get_magazine(self, location, line, floor, machine_type):
        """
        Hàm này gửi thông tin muốn nhận magazine tới máy
        """
        try:
            # Tìm máy để nhận magazine
            target_client = next(
                (
                    client
                    for client, info in socket_server.client_info.items()
                    if info["location"] == location
                ),
                None,
            )
            if target_client:
                messsage = {"line": line, "floor": floor, "machine_type": machine_type}
                json_message = json.dumps(messsage)
                socket_server.broadcast_message(json_message, target_client)
                print(f"Đã gửi thông tin muốn nhận magazine tới máy {location}")
            else:
                raise ValueError(
                    f"Không tìm thấy máy để nhận magazine tại vị trí {location}"
                )
        except Exception as e:
            logging.error(
                f"Lỗi trong quá trình gửi thông tin muốn nhận magazine: {str(e)}"
            )
            raise

    def process_handle_tranfer_goods(
        self, floor, direction, location, type, line, machine_type
    ):
        """
        Hàm này xử lý quá trình chuyển hàng giữa robot và máy
        """
        try:
            # Kiểm tra nếu là tầng 2 thì điều khiển năng băng tải
            if floor == 2:
                self.control_folk_conveyor(HEIGHT_LINE_25)
                print("Robot nâng băng tải tầng 2")

            # Robot mở stopper
            self.control_robot_stopper(direction, "open")

            # Gửi thông tin đến máy
            self.request_get_magazine(location, line, floor, machine_type)

            # Robot quay băng tải
            self.control_robot_conveyor(direction)
            print("Robot quay băng tải để chuyển hàng với máy")

            if type == "pick_up":
                # Kiểm tra xem robot đã nhận magazine từ máy
                while self.check_conveyor_robot(direction):
                    print("Robot chưa nhận magazine từ máy!!!")
                    asyncio.sleep(3)
                print("Robot đã nhận magazine từ máy!!!")
                self.request_get_magazine(location, line, 0, machine_type)
            elif type == "drop_off":
                # Kiểm tra xem máy đã nhận magazine
                i = floor - 1
                data_check = ""
                while not data_check["floor"][i] == 0:
                    print("Máy chưa nhận xong magazine!!!")
                    data_check = self.get_data_from_socket_server()
            # Robot đóng stopper
            self.control_robot_stopper(direction, "close")

            # Robot dừng băng tải
            self.control_robot_conveyor("stop")
        except Exception as e:
            logging.error(
                f"Xảy ra lỗi trong quá trình chuyển hàng giữa robot và máy: {str(e)}"
            )
            raise

    def handle_magazine_process(self):
        while self.mission:
            try:
                # Trích xuất thông tin từ danh sách nhiệm vụ
                pick_up = self.mission[0]["pick_up"]
                destination = self.mission[0]["destination"]
                floor = self.mission[0]["floor"]
                line = self.mission[0]["line"]
                machine_type = self.mission[0]["machine_type"]
                print(f"Pickup: {pick_up}, dropoff: {destination}")
                dir_pick_up = self.direction_conveyor(pick_up)
                dir_destination = self.direction_conveyor(destination)

                # Điều khiển robot tới vị trí lấy magazine
                self.control_robot_to_location(pick_up)

                # Kiểm tra xem robot đã tới vị trí lấy magazine
                self.check_location_robot(pick_up)

                # Xử lý chuyển hàng giữa robot và máy
                self.process_handle_tranfer_goods(
                    floor, dir_pick_up, pick_up, "pick_up", line, machine_type
                )

                # Gửi nhiệm vụ theo yêu cầu cho Buffer
                buffer_action(action=BUFFER_ACTION)

                # Điều khiển robot tới vị trí buffer
                self.control_robot_to_location(BUFFER_LOCATION)

                # Kiểm tra xem robot đã tới vị trí buffer
                while not self.check_location_robot(BUFFER_LOCATION):
                    print("Robot chưa tới vị trí buffer!!!")
                    asyncio.sleep(3)
                print("Robot đã tới vị trí buffer!!!")

                # Buffer quay băng tải để nhận magazine
                allow_transfer_magazine()
                asyncio.sleep(3)

                # Robot mở stopper
                self.control_robot_stopper("cw", "open")

                # Robot quay băng tải để truyền magazine vào buffer
                self.control_robot_conveyor("ccw")
                print("Robot quay băng tải để truyền magazine vào Buffer")

                # Chờ buffer xác nhận đã nhận xong magazine
                while not confirm_transfer_magazine():
                    print("Buffer chưa hoàn thành nhận magazine!!!")
                    asyncio.sleep(3)
                print("Buffer đã nhận magazine!!!")

                # Robot dừng băng tải
                self.control_robot_conveyor("stop")

                # Chờ buffer xử lý xong và sẵn sàng để trả magazine
                while not confirm_receive_magazine():
                    print("Buffer chưa hoàn thành xử lý!!!")
                    asyncio.sleep(3)
                print("Buffer đã hoàn thành xử lý, robot có thể đến lấy!!!")

                # Robot quay băng tải để lấy magazine
                self.control_robot_conveyor("cw")
                print("Robot quay băng tải để nhận magazine")

                # Robot xác nhận muốn lấy magazine
                robot_wanna_receive_magazine()
                asyncio.sleep(3)

                # Kiểm tra xem robot đã nhận magazine từ buffer
                while self.check_conveyor_robot("cw"):
                    print("Robot chưa nhận magazine từ Buffer!!!")
                    asyncio.sleep(3)
                print("Robot đã nhận magazine từ Buffer!!!")

                # Robot đóng stopper
                self.control_robot_stopper("cw", "close")

                # Robot xác nhận đã lấy magazine xong
                robot_confirm_receive_magazine()

                # Điều khiển robot tới vị trí trả magazine
                self.control_robot_to_location(destination)

                # Kiểm tra xem robot đã tới vị trí trả magazine
                self.check_location_robot(destination)

                # Xử lý chuyển hàng giữa robot và máy
                self.process_handle_tranfer_goods(
                    floor, dir_destination, destination, "drop_off", line, machine_type
                )

                # Xóa nhiệm vụ đã hoàn thành
                self.mission.popleft()
                print(f"Nhiệm vụ đã hoàn thành: {self.mission}")

                return {"message": "Quá trình xử lý hoàn tất"}
            except requests.exceptions.RequestException as e:
                return {"error": f"Lỗi trong quá trình xử lý: {str(e)}"}

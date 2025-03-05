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
    HEIGHT_FLOOR_1_LINE_25,
    HEIGHT_FLOOR_2_LINE_25,
    HEIGHT_BUFFER,
)
from mongodb import BufferDatabase
from socket_server import SocketServer
import logging
from collections import deque
import json
import time

# buffer_db = BufferDatabase()

CW = []

# Khởi tạo socket server
socket_server = SocketServer()


class ProccessHandler:
    def __init__(self):
        self.robot_url = f"http://{ROBOT_HOST}:{ROBOT_PORT}"
        self.mission = []

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
        if flag.status_code == 200:
            data = flag.json()
            if str(data) == "True":
                print("Robot đã tới vị trí")
                return True
            else:
                print("Robot chưa tới vị trí")
                return False
        else:
            print("Yêu cầu không thành công")
            return False

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
                    "data": direction,
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

    def check_stopper_robot(self, action, status):
        try:
            if status not in ["open", "close"]:
                raise ValueError("Hành động đóng cửa phải là 'open' hoặc 'close'.")
            response = requests.get(
                f"{self.robot_url}/stopper",
                json={"action": action, "status": status},
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển cửa băng tải của robot. Mã trạng thái: {response.status_code}"
                )
            data = response.json()
            if str(data) == "True":
                print("Stopper da dung trang thai")
                return True
            else:
                print("Stopper chua dung trang thai")
                return False
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

    def check_lift_conveyor(self, height):
        try:
            response = requests.get(f"{self.robot_url}/lift?height={height}")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi kiểm tra nâng băng tải của robot. Mã trạng thái: {response.status_code}"
                )
            data = response.json()
            if str(data) == "True":
                print("Băng tải đã tới vị trí")
                return True
            else:
                print("Băng tải chưa tới vị trí")
                return False
            # print("Kiểm tra băng tải của robot đã được điều khiển thành công")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình điều khiển nâng băng tải của robot: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại khi kiểm tra nâng băng tải của robot"
            ) from e

    def check_sensor_robot(self):
        try:
            response = requests.get(f"{self.robot_url}/sensor")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    "Lỗi đường truyền khi kiểm tra sensor của robot"
                )
            data = response.json()
            return data
            # if data[6] == 0:
            #     return "Sensor trai"
            # elif data[5] == 0:
            #     return "Sensor phai"
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình kiểm tra sensor: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại trong kiểm tra sensor của robot"
            ) from e

    def check_sensor_left_robot(self):
        return self.check_sensor_robot()[6] == 0

    def check_sensor_right_robot(self):
        return self.check_sensor_robot()[5] == 0

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

    def get_mission_from_socket_server(self):
        try:
            # Lấy dữ liệu từ socket server
            data = socket_server.get_mission_data()
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
        floor = mission_data.get("floor")
        machine_type = mission_data.get("machine_type")

        if not line or not machine_type or not floor:
            raise ValueError(
                "Thiếu thông tin line hoặc machine_type hoặc floor trong dữ liệu nhận được"
            )

        return line, machine_type, floor

    def _create_mission_from_data(self, line, machine_type, floor):
        """Tạo nhiệm vụ từ dữ liệu đã xác thực"""
        if line is not None:
            if line not in MAP_LINE:
                raise ValueError(f"Không tìm thấy thông tin cho line: {line}")

            station = MAP_LINE[line]
            pick_up, destination = (
                (station[0], station[1]) if floor == 2 else (station[1], station[0])
            )

            # Xử lý tạo nhiệm vụ nếu có thông tin tầng
            new_mission = {
                "pick_up": pick_up,
                "destination": destination,
                "floor": floor,
                "line": line,
                "machine_type": machine_type,
            }
            if not self.is_duplicate_mission(new_mission):
                if floor == 1:
                    insert_pos = 0
                    for i, mission in enumerate(self.mission):
                        if mission["floor"] == 2:
                            insert_pos = i
                            break
                        insert_pos = i + 1
                    self.mission.insert(insert_pos, new_mission)
                else:
                    self.mission.append(new_mission)
                logging.info(f"Đã thêm nhiệm vụ mới: {new_mission}")
            # else:
            #     raise ValueError("Nhiệm vụ này đã tồn tại trong danh sách chờ")

    def create_mission(self, data):
        """Hàm này lấy thông tin nhiệm vụ từ socket server và thêm vào danh sách nhiệm vụ."""
        try:
            line = data.get("line")
            floor = data.get("floor")
            machine_type = data.get("machine_type")

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
            height = 0
            if floor == 2:
                height = HEIGHT_FLOOR_2_LINE_25
            elif floor == 1:
                height = HEIGHT_FLOOR_1_LINE_25
            self.control_folk_conveyor(height)
            print("Robot nâng băng tải")

            # Kiểm tra xem băng tải đã được nâng tới đúng tầng chưa
            while not self.check_lift_conveyor(height):
                print("Robot chưa đạt độ cao băng tải")
                asyncio.sleep(6)

            # Robot mở stopper
            self.control_robot_stopper(direction, "open")

            # Kiểm tra robot đã mở stopper chưa
            while not self.check_stopper_robot(direction, "open"):
                print("Stopper chưa mở")
                asyncio.sleep(6)

            # Gửi thông tin đến máy
            self.request_get_magazine(location, line, floor, machine_type)

            # Robot quay băng tải
            self.control_robot_conveyor(direction)
            print("Robot quay băng tải để chuyển hàng với máy")

            # Kiểm tra robot đã quay băng tải chưa
            while not self.check_conveyor_robot(direction):
                print("Robot chưa hoàn thành điểu khiển quay băng tải")
                asyncio.sleep(20)

            if type == "pick_up":
                # Kiểm tra xem robot đã nhận magazine từ máy
                while not self.check_sensor_left_robot():
                    print("Robot chưa nhận magazine từ máy!!!")
                    asyncio.sleep(3)
                print("Robot đã nhận magazine từ máy!!!")
                self.request_get_magazine(location, line, 0, machine_type)
            elif type == "drop_off":
                # Kiểm tra xem máy đã nhận magazine
                i = floor - 1
                data_check = ""
                while data_check["floor"][i] != 0:
                    print("Máy chưa nhận xong magazine!!!")
                    data_check = self.get_data_from_socket_server()
            # Robot đóng stopper
            self.control_robot_stopper(direction, "close")

            # Kiểm tra robot đã đóng stopper chưa
            while not self.check_stopper_robot(direction, "close"):
                print("Stopper chưa đóng")
                asyncio.sleep(6)

            # Robot dừng băng tải
            self.control_robot_conveyor("stop")

            # Kiểm tra robot đã dừng băng tải chưa
            while not self.check_conveyor_robot("stop"):
                print("Robot chưa hoàn thành điểu khiển dừng băng tải")
                asyncio.sleep(20)

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

                # Điều khiển robot tới vị trí buffer
                self.control_robot_to_location(BUFFER_LOCATION)

                # Kiểm tra xem robot đã tới vị trí buffer
                while not self.check_location_robot(BUFFER_LOCATION):
                    print("Robot chưa tới vị trí buffer!!!")
                    asyncio.sleep(3)
                print("Robot đã tới vị trí buffer!!!")

                self.control_folk_conveyor(HEIGHT_BUFFER)

                # Gửi nhiệm vụ theo yêu cầu cho Buffer
                buffer_action(action=BUFFER_ACTION)
                asyncio.sleep(3)

                # Robot mở stopper
                self.control_robot_stopper("cw", "open")

                # Kiểm tra robot đã mở stopper chưa
                while not self.check_stopper_robot("cw", "open"):
                    print("Stopper chưa mở")
                    asyncio.sleep(6)

                # Robot quay băng tải để truyền magazine vào buffer
                self.control_robot_conveyor("ccw")
                print("Robot quay băng tải để truyền magazine vào Buffer")

                # Kiểm tra robot đã quay băng tải chưa
                while not self.check_conveyor_robot("ccw"):
                    print("Robot chưa hoàn thành điều khiển quay băng tải")
                    asyncio.sleep(2)

                # Chờ buffer xác nhận đã nhận xong magazine
                while confirm_transfer_magazine() != 0:
                    print("Buffer chưa hoàn thành nhận magazine!!!")
                    asyncio.sleep(3)
                print("Buffer đã nhận magazine!!!")

                # Robot dừng băng tải
                self.control_robot_conveyor("stop")

                # Kiểm tra robot đã dừng băng tải chưa
                while not self.check_conveyor_robot("stop"):
                    print("Robot chưa hoàn thành điều khiển dừng băng tải")
                    asyncio.sleep(2)

                # Chờ buffer xử lý xong và sẵn sàng để trả magazine
                while not confirm_receive_magazine():
                    print("Buffer chưa hoàn thành xử lý!!!")
                    asyncio.sleep(3)
                print("Buffer đã hoàn thành xử lý, robot có thể đến lấy!!!")

                # Robot quay băng tải để lấy magazine
                self.control_robot_conveyor("cw")
                print("Robot quay băng tải để nhận magazine")

                # Kiểm tra robot đã thành công điều khiển băng tải
                while not self.check_conveyor_robot("cw"):
                    print("Robot chưa hoàn thành điều khiển băng tải")
                    asyncio.sleep(6)

                # Robot xác nhận muốn lấy magazine
                robot_wanna_receive_magazine()
                asyncio.sleep(3)

                # Kiểm tra xem robot đã nhận magazine từ buffer
                while not self.check_sensor_left_robot():
                    print("Robot chưa nhận magazine từ Buffer!!!")
                    asyncio.sleep(3)
                print("Robot đã nhận magazine từ Buffer!!!")

                # Điều khiển dừng băng tải của robot
                self.control_robot_conveyor("stop")

                # Kiểm tra robot đã dừng băng tải chưachưa
                while not self.check_conveyor_robot("stop"):
                    print("Robot chưa hoàn thành điều khiển dừng băng tải")
                    time.sleep(6)

                # Robot đóng stopper
                self.control_robot_stopper("cw", "close")

                # Kiểm tra robot đã đóng stopper chưa
                while not self.check_stopper_robot("cw", "close"):
                    print("Stopper chưa đúng trạng thái")
                    asyncio.sleep(6)

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

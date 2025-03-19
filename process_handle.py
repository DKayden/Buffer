import requests
import asyncio
from buffer import (
    confirm_transfer_magazine,
    confirm_receive_magazine,
    buffer_action,
    robot_wanna_receive_magazine,
    robot_confirm_receive_magazine,
    buffer_allow_action,
    buffer_turn,
)
from config import (
    ROBOT_HOST,
    ROBOT_PORT,
    BUFFER_LOCATION,
    MAP_LINE,
    HEIGHT_BUFFER,
    STANDBY_LOCATION,
    LINE_CONFIG,
)
from mongodb import BufferDatabase
from socket_server import SocketServer
import logging
from collections import deque
import json
import time

# buffer_db = BufferDatabase()

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
                print("Stopper đã đúng trạng thái")
                return True
            else:
                print("Stopper chưa đúng trạng thái")
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

    def get_information_sensor_robot(self):
        try:
            response = requests.get(f"{self.robot_url}/sensor")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    "Lỗi đường truyền khi kiểm tra sensor của robot"
                )
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            print(f"Lỗi trong quá trình kiểm tra sensor: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại trong kiểm tra sensor của robot"
            ) from e

    def check_sensor_left_robot(self):
        return self.get_information_sensor_robot()[6] == 0

    def check_sensor_right_robot(self):
        return self.get_information_sensor_robot()[5] == 0

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

    def create_mission(self):
        """Hàm này lấy thông tin nhiệm vụ từ socket server và thêm vào danh sách nhiệm vụ."""
        try:
            data = self.get_mission_from_socket_server()
            while not data:
                data = self.get_mission_from_socket_server()
                print("Chưa có dữ liệu nhiệm vụ từ socker server")
                time.sleep(3)
            line = data.get("line")
            floor = data.get("floor")
            machine_type = data.get("machine_type")

            self._create_mission_from_data(line, machine_type, floor)

        except Exception as e:
            logging.error(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")
            raise

    def send_signal_to_call(self, location, line, floor, machine_type):
        """
        Hàm này gửi thông tin tới bộ call
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
                print(f"Đã gửi thông tin tới vị trí {location}")
            else:
                raise ValueError(f"Không tìm thấy máy tại vị trí {location}")
        except Exception as e:
            logging.error(f"Lỗi trong quá trình gửi thông tin: {str(e)}")
            raise

    def process_tranfer_at_point(self, location, line, machine_type, floor):
        # Xử lý điều khiển robot tới điểm
        self.control_robot_to_location(location)
        while not self.check_location_robot(location):
            time.sleep(3)

        # Xử lý điều khiển băng tải tới độ cao
        height = LINE_CONFIG.get((line, machine_type, floor), {}).get("line_height")
        self.control_folk_conveyor(height)
        while not self.check_lift_conveyor(height):
            time.sleep(1)

        # Xử lý điều khiển mở stopper
        stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "stopper_action"
        )
        self.control_robot_stopper(stopper_action, "open")
        while not self.check_stopper_robot(stopper_action, "open"):
            time.sleep(1)

        # Xử lý quay băng tải
        direction = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "conveyor_direction"
        )
        self.control_robot_conveyor(direction)
        while not self.check_conveyor_robot(direction):
            print("Băng tải chưa hoàn thành điều khiển quay")

        # Gửi tín hiệu xuống bộ call để quay băng tải của máy sản xuất
        if floor == 1:
            infor_floor = [1, 0]
        elif floor == 2:
            infor_floor = [0, 2]
        self.send_signal_to_call(location, line, infor_floor, machine_type)

        # Kiểm tra đã trao đổi hàng chưa
        sensor_check = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "sensor_check"
        )
        if sensor_check == "right":
            while not self.check_sensor_right_robot():
                print(f"Robot chưa thực hiện trao đổi hàng xong tại {location}!!!")
        else:
            while not self.check_sensor_left_robot():
                print(f"Robot chưa thực hiện trao đổi hàng xong tại {location}!!!")
        print(f"Robot đã thực hiện xong trao đổi hàng tại {location}")

        # Gửi tín hiệu xuống bộ call để dừng băng tải của máy sản xuất
        self.send_signal_to_call(location, line, [0, 0], machine_type)

        # Xử lý dừng băng tải
        self.control_robot_conveyor("stop")
        while not self.check_conveyor_robot("stop"):
            print("Băng tải chưa hoàn thành điều khiển dừng")

        # Xử lý đóng stopper
        self.control_robot_stopper(stopper_action, "close")
        while not self.check_stopper_robot(stopper_action, "close"):
            print("Robot chưa đóng stopper")

    def handle_process_buffer(self, line, machine_type, floor):
        # Xử lý điều khiển robot tới điểm Bufffer
        self.control_robot_to_location(BUFFER_LOCATION)
        while not self.check_location_robot(BUFFER_LOCATION):
            time.sleep(3)

        # Xử lý điều khiển băng tải tới độ cao của Buffer
        self.control_folk_conveyor(HEIGHT_BUFFER)
        while not self.check_lift_conveyor(HEIGHT_BUFFER):
            time.sleep(1)

        #  Kiểm tra trạng thái của Buffer
        while not buffer_allow_action():
            print("Buffer chưa sẵn sàng")
        print("Buffer đã sẵn sàng")

        # Xử lý gửi lệnh thực thi cho Buffer
        turn = LINE_CONFIG.get((line, machine_type, floor), {}).get("buffer_turn")
        action = LINE_CONFIG.get((line, machine_type, floor), {}).get("buffer_action")
        buffer_turn(turn)
        buffer_action(action)

        # Xử lý điều khiển mở stopper tại Buffer
        self.control_robot_stopper("cw", "open")
        while not self.check_stopper_robot("cw", "open"):
            time.sleep(1)

        # Xử lý quay băng tải tại Buffer
        self.control_robot_conveyor("ccw")
        while not self.check_conveyor_robot("ccw"):
            print("Robot chưa hoàn thành điều khiển quay băng tải")

        # Kiểm tra Buffer đã nhận hàng chưa
        while confirm_transfer_magazine() != 0:
            print("Buffer đang chuyển hàng, vui lòng chờ...")

        # Xử lý dừng băng tải robot tại Buffer
        self.control_robot_conveyor("stop")
        while not self.check_conveyor_robot("stop"):
            print("Robot chưa hoàn thành điều khiển dừng băng tải")

        # Kiểm tra Buffer đã xử lý xong chưa
        while not confirm_receive_magazine():
            print("Buffer chưa xử lý xong hàng, vui lòng chờ...")

        # Xử lý quay băng tải robot để nhận lại hàng từ Buffer
        self.control_robot_conveyor("cw")
        while not self.check_conveyor_robot("cw"):
            print("Robot chưa hoàn thành điều khiển quay băng tải")

        # Gửi thông tin robot muốn nhận hàng cho Buffer
        robot_wanna_receive_magazine()

        # Kiểm tra robot đã nhận hàng chưa
        while not self.check_sensor_left_robot():
            print("Robot chưa nhận hàng tại Buffer!!!")

        # Xử lý dừng băng tải của robot
        self.control_robot_conveyor("stop")
        while not self.check_conveyor_robot("stop"):
            print("Robot chưa hoàn thành điều khiển dừng băng tải")

        # Xử lý đóng stopper của robot
        self.control_robot_stopper("cw", "close")
        while not self.check_stopper_robot("cw", "close"):
            print("Robot chưa đóng stopper")

        # Gửi thông tin xác nhận robot đã nhận hàng cho Buffer
        robot_confirm_receive_magazine()

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

                if machine_type == "loader":
                    pick_up_type = "unloader"
                    destination_type = machine_type
                elif machine_type == "unloader":
                    pick_up_type = "loader"
                    destination_type = machine_type

                # Xử lý điều khiển robot tới pickup
                self.process_tranfer_at_point(pick_up, line, pick_up_type, floor)

                # Xử lý chu trình Buffer
                self.handle_process_buffer(line, destination_type, floor)

                # Xử lý điều khiển robot tới điểm destination
                self.process_tranfer_at_point(
                    destination, line, destination_type, floor
                )

                # Xóa nhiệm vụ đã hoàn thành
                self.mission.pop(0)
                print(f"Nhiệm vụ đã hoàn thành: {self.mission[0]}")

                #  Xử lý điều khiển robot về standby
                self.control_robot_to_location(STANDBY_LOCATION)
                while not self.check_location_robot(STANDBY_LOCATION):
                    time.sleep(3)

                return {"message": "Quá trình xử lý hoàn tất"}
            except requests.exceptions.RequestException as e:
                return {"error": f"Lỗi trong quá trình xử lý: {str(e)}"}

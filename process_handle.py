import requests
import asyncio
from buffer import (
    confirm_transfer_magazine,
    confirm_receive_magazine,
    buffer_action,
    robot_wanna_receive_magazine,
    robot_confirm_receive_magazine,
    buffer_allow_action,
)
from config import (
    ROBOT_HOST,
    ROBOT_PORT,
    BUFFER_LOCATION,
    MAP_LINE,
    HEIGHT_BUFFER,
    STANDBY_LOCATION,
    LINE_CONFIG,
    CHARGE_LOCATION,
)
from mongodb import BufferDatabase
from socket_server import SocketServer
import logging
from collections import deque
import json
import time
import state

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
            self.write_message_on_GUI(f"Robot di chuyển tới: {location}")

        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển di chuyển của robot: {str(e)}"
            )
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
                self.write_message_on_GUI(f"Robot đã tới vị trí {location}")
                return True
            else:
                self.write_message_on_GUI(f"Robot chưa tới vị trí {location}")
                return False
        else:
            self.write_message_on_GUI("Yêu cầu kiểm tra vị trí không thành công")
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
            self.write_message_on_GUI("Băng tải của robot đã được điều khiển")
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển băng tải của robot: {str(e)}"
            )
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
            self.write_message_on_GUI(
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
            self.write_message_on_GUI(
                "Cửa băng tải của robot đã được điều khiển thành công"
            )
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển cửa băng tải của robot: {str(e)}"
            )
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
                self.write_message_on_GUI("Stopper đã đúng trạng thái")
                return True
            else:
                self.write_message_on_GUI("Stopper chưa đúng trạng thái")
                return False
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển cửa băng tải của robot: {str(e)}"
            )
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
            self.write_message_on_GUI(
                "Nâng băng tải của robot đã được điều khiển thành công"
            )
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển nâng băng tải của robot: {str(e)}"
            )
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
                self.write_message_on_GUI(f"Băng tải đã tới độ cao {height}")
                return True
            else:
                self.write_message_on_GUI(f"Băng tải chưa tới độ cao {height}")
                return False
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển nâng băng tải của robot: {str(e)}"
            )
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
            self.write_message_on_GUI(f"Lỗi trong quá trình kiểm tra sensor: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại trong kiểm tra sensor của robot"
            ) from e

    def check_sensor_left_robot(self):
        return self.get_information_sensor_robot()[6] == 0

    def check_sensor_right_robot(self):
        return self.get_information_sensor_robot()[5] == 0

    def control_led(self, color):
        """
        Hàm này điều khiển led của robot.
        """
        try:
            response = requests.post(
                f"{self.robot_url}/color",
                json={
                    "color": color,
                },
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển led của robot. Mã trạng thái: {response.status_code}"
                )
            # self.write_message_on_GUI(f"Led của robot đã chuyển thành {color}")
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển led của robot: {str(e)}"
            )
            raise requests.exceptions.RequestException(
                "Thất bại khi điều khiển led của robot"
            ) from e

    def get_data_status_robot(self):
        try:
            response = requests.get(f"{self.robot_url}/status")
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    "Lỗi đường truyền khi kiểm tra status của robot"
                )
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(f"Lỗi trong quá trình kiểm tra status: {str(e)}")
            raise requests.exceptions.RequestException(
                "Thất bại trong kiểm tra status của robot"
            ) from e

    def control_navigate_action(self, type):
        try:
            response = requests.get(
                f"{self.robot_url}/action?type={type}",
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển action của robot. Mã trạng thái: {response.status_code}"
                )
            self.write_message_on_GUI("Action của robot đã được điều khiển thành công")
        except requests.exceptions.RequestException as e:
            self.write_message_on_GUI(
                f"Lỗi trong quá trình điều khiển action của robot: {str(e)}"
            )
            raise requests.exceptions.RequestException(
                "Thất bại khi điều khiển action của robot"
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
            self.write_message_on_GUI(
                f"Lỗi trong quá trình lấy dữ liệu từ socket server: {str(e)}"
            )
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
            self.write_message_on_GUI(
                f"Lỗi trong quá trình lấy dữ liệu từ socket server: {str(e)}"
            )
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
                # if floor == 1:
                #     insert_pos = 0
                #     for i, mission in enumerate(self.mission):
                #         if mission["floor"] == 2:
                #             insert_pos = i
                #             break
                #         insert_pos = i + 1
                #     self.mission.insert(insert_pos, new_mission)
                # else:
                self.mission.append(new_mission)
                socket_server.remove_first_mission()
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
            # socket_server.remove_first_mission()

        except Exception as e:
            logging.error(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")
            raise

    def send_message_to_call(self, target_ip, line, machine_type, infor_floor):
        """
        Hàm này gửi thông tin tới máy
        """
        try:
            # Tìm máy để nhận magazine
            if target_ip:
                messsage = {
                    "line": line,
                    "floor": infor_floor,
                    "machine_type": machine_type,
                }
                json_message = json.dumps(messsage)
                socket_server.broadcast_message(json_message, target_ip)
                self.write_message_on_GUI(
                    f"Đã gửi thông tin tới máy {target_ip.getpeername()[0]}"
                )
            # else:
            #     raise ValueError(
            #         f"Không tìm thấy máy để nhận magazine tại vị trí {target_ip}"
            #     )
        except Exception as e:
            logging.error(
                f"Lỗi trong quá trình gửi thông tin muốn nhận magazine: {str(e)}"
            )
            self.send_message_to_call(target_ip, line, machine_type, infor_floor)
            # raise

    def add_line_auto(self, line):
        # with state.line_auto_web_lock:
        # if line not in state.line_auto_web_lock:
        state.line_auto_web = line

    def remove_line_auto(self, line):
        with state.line_auto_web_lock:
            if line in state.line_auto_web:
                state.line_auto_web.remove(line)

    def is_line_auto(self, line):
        # with state.line_auto_web_lock:
        return line in state.line_auto_web

    def read_robot_status(self):
        state.data_status.update(self.get_data_status_robot())
        call_status = {
            "Call_Load_L25": state.call_status["call_loader_line25"],
            "Call_Load_L26": state.call_status["call_loader_line26"],
            "Call_Load_L27": state.call_status["call_loader_line27"],
            "Call_Load_L28": state.call_status["call_loader_line28"],
            "Call_UnLoad_L25": state.call_status["call_unloader_line25"],
            "Call_UnLoad_L26": state.call_status["call_unloader_line26"],
            "Call_UnLoad_L27": state.call_status["call_unloader_line27"],
            "Call_UnLoad_L28": state.call_status["call_unloader_line28"],
        }
        magazine_status = state.magazine_status

        data_sensor = [
            self.get_information_sensor_robot()[5],
            self.get_information_sensor_robot()[6],
        ]

        if state.data_status["blocked"] or state.data_status["emergency"]:
            self.control_led("red")
            robot_led = "red"
        elif (
            state.data_status["current_station"] == CHARGE_LOCATION
            or state.data_status["battery_level"] < 0.2
        ):
            self.control_led("yellow")
            robot_led = "yellow"
        else:
            self.control_led("green")
            robot_led = "green"

        state.data_status["led"] = robot_led
        state.data_status["callStatus"] = call_status
        state.data_status["magazine_status"] = magazine_status
        state.data_status["message"] = state.messenge
        state.data_status["history"] = state.history
        state.data_status["mode"] = state.mode
        state.data_status["idle"] = state.robot_status
        state.data_status["sensors"] = data_sensor
        return state.data_status

    def write_message_on_GUI(self, message=""):
        state.messenge = message

    def write_history(self, status, type, mission, floor):
        state.history = {
            "status": status,
            "type": type,
            "mission": mission,
            "floor": floor,
        }

    def handle_charge_battery(self):
        try:
            if state.data_status["battery_level"] < 0.2:
                self.control_robot_to_location(CHARGE_LOCATION)
                while not self.check_location_robot(CHARGE_LOCATION):
                    self.write_message_on_GUI("Robot chưa hoàn thành di chuyển tới vị trí nạp pin")
                    time.sleep(6)
                while state.data_status["battery_level"] < 0.9:
                    self.write_message_on_GUI("Robot chưa hoàn thành nạp pin")
                    time.sleep(6)
                self.control_robot_to_location(STANDBY_LOCATION)
                while not self.check_location_robot(STANDBY_LOCATION):
                    self.write_message_on_GUI("Robot chưa hoàn thành di chuyển tới vị trí standby")
                    time.sleep(6)
        except Exception as e:
            logging.error(f"Lỗi trong quá trình nạp pin: {str(e)}")
            raise

    def process_handle_tranfer_goods(self, location, line, machine_type, floor, type):
        """
        Hàm này xử lý quá trình chuyển hàng giữa robot và máy
        """
        try:
            self.control_robot_to_location(location)
            print(f"Robot dang di chuyen toi {location}")
            while not self.check_location_robot(location):
                print(f"Robot chua hoan thanh di chuyen toi {location}")
                time.sleep(6)
            height = LINE_CONFIG.get((line, machine_type, floor), {}).get("line_height")
            self.control_folk_conveyor(height)
            while not self.check_lift_conveyor(height):
                print("Robot chua dat do cao bang tai")
            stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
                "stopper_action"
            )
            self.control_robot_stopper(stopper_action, "open")
            while not self.check_stopper_robot(stopper_action, "open"):
                print("Stopper chua dung trang thai")
                # time.sleep(3)
            direction = LINE_CONFIG.get((line, machine_type, floor), {}).get(
                "conveyor_direction"
            )
            self.control_robot_conveyor(direction)
            while not self.check_conveyor_robot(direction):
                print("Chua hoan thanh dieu khien bang tai")
            target_ip = LINE_CONFIG.get((line, machine_type, floor), {}).get("address")
            # print("Target ID: ", target_ip)
            target = socket_server.get_client_socket_by_ip(target_ip)
            # print("Target: ", target)
            self.send_message_to_call(target, line, machine_type, floor)
            sensor_check = LINE_CONFIG.get((line, machine_type, floor), {}).get(
                "sensor_check"
            )
            if type == "pickup":
                if sensor_check == "right":
                    while not self.check_sensor_right_robot():
                        print("Chua hoan thanh nhan hang")
                        time.sleep(1)
                elif sensor_check == "left":
                    while not self.check_sensor_left_robot():
                        print("Chua hoan thanh nhan hang")
                        time.sleep(1)
            if type == "destination":
                while self.check_sensor_right_robot() or self.check_sensor_left_robot():
                    print("Chua hoan thanh tra hang")
                    time.sleep(15)
            self.control_robot_conveyor("stop")
            while not self.check_conveyor_robot("stop"):
                print("Chua hoan thanh dieu khien bang tai")
                # time.sleep(6)
            self.control_robot_stopper(stopper_action, "close")
            while not self.check_stopper_robot(stopper_action, "close"):
                print("Stopper chua dung trang thai")
                # time.sleep(3)
            self.send_message_to_call(target, line, machine_type, 0)

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
                while not self.check_location_robot(pick_up):
                    print("Robot chưa tới vị trí lấy magazine!!!")
                    asyncio.sleep(3)

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

                # Điều khiển chiều cao băng tải để tranfer hàng với buffer
                self.control_folk_conveyor(HEIGHT_BUFFER)

                # Kiểm tra xem chiều cao băng tải đã đạt yêu cầu chưa
                while not self.check_lift_conveyor(HEIGHT_BUFFER):
                    print("Robot chưa đạt độ cao băng tải")
                    asyncio.sleep(6)

                # Kiểm tra Buffer đã sẵn sàng thao tác chưa
                while not buffer_allow_action():
                    print("Buffer chua san sang")

                # Gửi nhiệm vụ theo yêu cầu cho Buffer
                action = self.line_configs.get((line, machine_type, floor), {}).get(
                    "action"
                )
                buffer_action(action)
                # asyncio.sleep(3)

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
                print("Robot đã tới vị trí trả magazine!!!")

                # Kiểm tra xem robot đã tới vị trí trả magazine
                while not self.check_location_robot(destination):
                    print("Robot chưa tới vị trí trả magazine!!!")
                    asyncio.sleep(3)

                # Xử lý chuyển hàng giữa robot và máy
                self.process_handle_tranfer_goods(
                    floor, dir_destination, destination, "drop_off", line, machine_type
                )

                # Xóa nhiệm vụ đã hoàn thành
                self.mission.pop(0)
                print(f"Nhiệm vụ đã hoàn thành: {self.mission}")

                # Điều khiển robot tới vị trí standby
                self.control_robot_to_location(STANDBY_LOCATION)
                print("Robot đã tới vị trí standby!!!")

                # Kiểm tra xem robot đã tới vị trí standby
                while not self.check_location_robot(STANDBY_LOCATION):
                    print("Robot chưa tới vị trí standby!!!")
                    asyncio.sleep(3)

                return {"message": "Quá trình xử lý hoàn tất"}
            except requests.exceptions.RequestException as e:
                return {"error": f"Lỗi trong quá trình xử lý: {str(e)}"}

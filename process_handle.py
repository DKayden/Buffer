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


# Khởi tạo socket server
socket_server = SocketServer()


class ProccessHandler:
    def __init__(self):
        self.robot_url = f"http://{ROBOT_HOST}:{ROBOT_PORT}"

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
                return True
            else:
                return False
        else:
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
            self.get_data_status_robot()
        except Exception as ex:
            logging.error(f"Xảy ra lỗi khi lấy dữ liệu robot: {ex}")

    def control_navigate_action(self, type):
        try:
            response = requests.get(
                f"{self.robot_url}/action?type={type}",
            )
            if response.status_code != 200:
                raise requests.exceptions.RequestException(
                    f"Lỗi đường truyền khi điều khiển action của robot. Mã trạng thái: {response.status_code}"
                )
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
        for mission in state.mission:
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
                #     for i, mission in enumerate(state.mission):
                #         if mission["floor"] == 2:
                #             insert_pos = i
                #             break
                #         insert_pos = i + 1
                #     state.mission.insert(insert_pos, new_mission)
                # else:
                state.mission.append(new_mission)
                socket_server.remove_first_mission()
                logging.info(f"Đã thêm nhiệm vụ mới: {new_mission}")

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
        except Exception as e:
            logging.error(
                f"Lỗi trong quá trình gửi thông tin muốn nhận magazine: {str(e)}"
            )
            self.send_message_to_call(target_ip, line, machine_type, infor_floor)

    def add_line_auto(self, line):
        state.line_auto_web = line

    def remove_line_auto(self, line):
        with state.line_auto_web_lock:
            if line in state.line_auto_web:
                state.line_auto_web.remove(line)

    def is_line_auto(self, line):
        return line in state.line_auto_web

    def read_robot_status(self):
        try:
            call_status = {
                "Call_Load_L25": state.call_status["call_loader_line25"],
                "Call_Load_L26": state.call_status["call_loader_line26"],
                "Call_Load_L27": state.call_status["call_loader_line27"],
                "Call_Load_L28": state.call_status["call_loader_line28"],
                "Call_UnLoad_L25": state.call_status["call_unloader_line25"],
                "Call_UnLoad_L26": state.call_status["call_unloader_line26"],
                "Call_UnLoad_L27": state.call_status["call_unloader_line27"],
                "Call_UnLoad_L28": state.call_status["call_unloader_line28"],
                "Call_Load_L25_1": state.call_status["call_loader_line25_1"],
                "Call_UnLoad_L25_1": state.call_status["call_unloader_line25_1"],
                "Call_Load_L25_2": state.call_status["call_loader_line25_2"],
                "Call_UnLoad_L25_2": state.call_status["call_unloader_line25_2"],
                "Call_Load_L26_1": state.call_status["call_loader_line26_1"],
                "Call_UnLoad_L26_1": state.call_status["call_unloader_line26_1"],
                "Call_Load_L26_2": state.call_status["call_loader_line26_2"],
                "Call_UnLoad_L26_2": state.call_status["call_unloader_line26_2"],
                "Call_Load_L27_1": state.call_status["call_loader_line27_1"],
                "Call_UnLoad_L27_1": state.call_status["call_unloader_line27_1"],
                "Call_Load_L27_2": state.call_status["call_loader_line27_2"],
                "Call_UnLoad_L27_2": state.call_status["call_unloader_line27_2"],
                "Call_Load_L28_1": state.call_status["call_loader_line28_1"],
                "Call_UnLoad_L28_1": state.call_status["call_unloader_line28_1"],
                "Call_Load_L28_2": state.call_status["call_loader_line28_2"],
                "Call_UnLoad_L28_2": state.call_status["call_unloader_line28_2"],
            }
            magazine_status = state.magazine_status

            state.data_status["callStatus"] = call_status
            state.data_status["magazine_status"] = magazine_status
            state.data_status["message"] = state.messenge
            state.data_status["history"] = state.history
            state.data_status["mode"] = state.mode
            state.data_status["idle"] = state.robot_status
            return state.data_status
        except Exception as e:
            logging.info(f"Xảy ra lỗi trong quá trình lấy trạng thái robot {e}")
            self.read_robot_status()

    def write_message_on_GUI(self, message=""):
        state.messenge = message

    def write_history(self, status, type, mission, floor):
        state.history = {
            "status": status,
            "type": type,
            "mission": mission,
            "floor": floor,
        }

    def handle_robot_charging(self):
        data = self.get_data_status_robot()
        if data and data["battery_level"] and data["battery_level"] < 0.2:
            self.write_message_on_GUI(f"Pin yếu! Cần sạc pin.")
            self.control_robot_to_location(CHARGE_LOCATION)
            while not self.check_location_robot(CHARGE_LOCATION):
                self.write_message_on_GUI(f"Robot chưa di chuyển đến vị trí sạc pin!")
                time.sleep(3)
            while data["battery_level"] < 0.8:
                self.write_message_on_GUI(f"Robot chưa sạc tới 80%")
                time.sleep(60)
            self.control_robot_to_location(STANDBY_LOCATION)

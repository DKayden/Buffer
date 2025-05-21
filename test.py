import logging
import time
import threading
import json
from socket_server import SocketServer
from config import (
    HEIGHT_BUFFER,
    BUFFER_LOCATION,
    LINE_CONFIG,
    STANDBY_LOCATION,
    CHARGE_LOCATION,
)
from process_handle import ProccessHandler
import buffer

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Khởi tạo các biến toàn cục
socket_server = SocketServer()
stop_threads = False
process_handler = ProccessHandler()


class TimeoutError(Exception):
    """Lỗi timeout"""

    pass


def wait_for_condition(condition_func, timeout=600, interval=1, error_message=""):
    """
    Chờ điều kiện được thỏa mãn với timeout

    Args:
        condition_func: Hàm kiểm tra điều kiện
        timeout: Thời gian tối đa chờ (giây)
        interval: Khoảng thời gian giữa các lần kiểm tra (giây)
        error_message: Thông báo lỗi khi timeout
    """
    start_time = time.time()
    while not condition_func():
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Timeout waiting for condition: {error_message}")
        time.sleep(interval)


def handle_robot_movement(location, error_message=""):
    """
    Xử lý di chuyển robot đến vị trí

    Args:
        location: Vị trí đích
        error_message: Thông báo lỗi khi timeout
    """
    try:
        process_handler.control_robot_to_location(location)
        logging.info(f"Robot đang di chuyển tới {location}")
        wait_for_condition(
            lambda: process_handler.check_location_robot(location),
            error_message=error_message,
        )
    except Exception as e:
        logging.error(f"Lỗi khi di chuyển robot tới {location}: {str(e)}")
        process_handler.control_robot_to_location(location)
        raise


def handle_conveyor_operations(line, machine_type, floor, type):
    """
    Xử lý các thao tác với băng tải

    Args:
        line: Tên line
        machine_type: Loại máy
        floor: Tầng
        type: Loại thao tác
    """
    try:
        height = LINE_CONFIG.get((line, machine_type, floor), {}).get("line_height")
        process_handler.control_folk_conveyor(height)
        wait_for_condition(
            lambda: process_handler.check_lift_conveyor(height),
            error_message="Robot chưa đạt độ cao băng tải",
        )

        stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "stopper_action"
        )
        process_handler.control_robot_stopper(stopper_action, "open")
        wait_for_condition(
            lambda: process_handler.check_stopper_robot(stopper_action, "open"),
            error_message="Stopper chưa đúng trạng thái",
        )

        direction = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "conveyor_direction"
        )
        process_handler.control_robot_conveyor(direction)
        wait_for_condition(
            lambda: process_handler.check_conveyor_robot(direction),
            error_message="Chưa hoàn thành điều khiển băng tải",
        )
    except Exception as e:
        logging.error(f"Lỗi khi xử lý băng tải: {str(e)}")
        raise


def handle_sensor_check(type, sensor_check):
    """
    Xử lý kiểm tra sensor

    Args:
        type: Loại kiểm tra
        sensor_check: Loại sensor cần kiểm tra
    """
    try:
        if type == "pickup":
            sensor_checks = {
                "right": process_handler.check_sensor_right_robot,
                "left": process_handler.check_sensor_left_robot,
            }

            if sensor_check in sensor_checks:
                wait_for_condition(
                    lambda: sensor_checks[sensor_check](),
                    error_message="Chưa hoàn thành nhận hàng",
                )
        elif type == "destination":
            time.sleep(9)
            wait_for_condition(
                lambda: not (
                    process_handler.check_sensor_right_robot()
                    or process_handler.check_sensor_left_robot()
                ),
                error_message="Chưa hoàn thành trả hàng",
            )
    except Exception as e:
        logging.error(f"Lỗi khi kiểm tra sensor: {str(e)}")
        raise


def handle_tranfer_magazine(location, line, machine_type, floor, type):
    """
    Xử lý quá trình chuyển magazine

    Args:
        location: Vị trí
        line: Tên line
        machine_type: Loại máy
        floor: Tầng
        type: Loại thao tác
    """
    try:
        process_handler.control_led("green")
        handle_robot_movement(
            location, f"Robot chưa hoàn thành di chuyển tới {location}"
        )
        handle_conveyor_operations(line, machine_type, floor, type)

        target_ip = LINE_CONFIG.get((line, machine_type, floor), {}).get("address")
        target = socket_server.get_client_socket_by_ip(target_ip)
        count = 5
        while count >= 0:
            process_handler.send_message_to_call(target, line, machine_type, floor)
            count = count - 1
            time.sleep(1)

        sensor_check = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "sensor_check"
        )
        handle_sensor_check(type, sensor_check)

        process_handler.control_robot_conveyor("stop")
        wait_for_condition(
            lambda: process_handler.check_conveyor_robot("stop"),
            error_message="Chưa hoàn thành điều khiển băng tải",
        )

        stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "stopper_action"
        )
        process_handler.control_robot_stopper(stopper_action, "close")
        wait_for_condition(
            lambda: process_handler.check_stopper_robot(stopper_action, "close"),
            error_message="Stopper chưa đúng trạng thái",
        )

        process_handler.control_folk_conveyor(50)
        process_handler.send_message_to_call(target, line, machine_type, 0)

    except Exception as e:
        logging.error(f"Lỗi trong quá trình chuyển magazine: {str(e)}")
        raise


def handle_mission_creation():
    """Xử lý tạo nhiệm vụ"""
    while not stop_threads:
        try:
            mission_data = socket_server.get_mission_data()
            if mission_data:
                process_handler.create_mission(mission_data)
            time.sleep(1)
        except Exception as e:
            logging.error(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")


def monitor_data():
    """Giám sát và xử lý dữ liệu"""
    while not stop_threads:
        try:
            if process_handler.mission:
                logging.info(f"Danh sách nhiệm vụ: {process_handler.mission}")
                mission = process_handler.mission[0]

                # if True:
                #     mission = {
                #     "pick_up": "LM282",
                #     "destination": "LM281",
                #     "floor": 2,
                #     "line": "line 28",
                #     "machine_type": "unloader",
                #     }

                pick_up = mission["pick_up"]
                destination = mission["destination"]
                floor = mission["floor"]
                line = mission["line"]
                machine_type = mission["machine_type"]

                pick_up_type = "unloader" if machine_type == "loader" else "loader"
                destination_type = machine_type

                handle_tranfer_magazine(pick_up, line, pick_up_type, floor, "pickup")

                handle_robot_movement(
                    BUFFER_LOCATION, "Robot chưa hoàn thành di chuyển tới buffer"
                )

                process_handler.control_folk_conveyor(HEIGHT_BUFFER)
                wait_for_condition(
                    lambda: process_handler.check_lift_conveyor(HEIGHT_BUFFER),
                    error_message="Robot chưa đạt độ cao băng tải",
                )

                process_handler.control_robot_stopper("cw", "open")
                wait_for_condition(
                    lambda: process_handler.check_stopper_robot("cw", "open"),
                    error_message="Stopper chưa đúng trạng thái",
                )

                wait_for_condition(
                    lambda: buffer.buffer_allow_action(),
                    error_message="Buffer chưa sẵn sàng",
                )

                buffer_route = LINE_CONFIG.get((line, destination_type, floor), {}).get(
                    "buffer_turn"
                )
                buffer.buffer_turn(buffer_route)

                buffer_action = LINE_CONFIG.get(
                    (line, destination_type, floor), {}
                ).get("buffer_action")
                buffer.buffer_action(buffer_action)

                process_handler.control_robot_conveyor("ccw")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("ccw"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                )

                time.sleep(20)
                process_handler.control_robot_conveyor("stop")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("stop"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                )

                wait_for_condition(
                    lambda: buffer.confirm_receive_magazine(),
                    error_message="Buffer chưa xử lý xong",
                )

                process_handler.control_robot_conveyor("cw")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("cw"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                )

                buffer.robot_wanna_receive_magazine()
                wait_for_condition(
                    lambda: process_handler.check_sensor_left_robot(),
                    error_message="Chưa hoàn thành nhận hàng",
                )

                process_handler.control_robot_conveyor("stop")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("stop"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                )

                process_handler.control_robot_stopper("cw", "close")
                wait_for_condition(
                    lambda: process_handler.check_stopper_robot("cw", "close"),
                    error_message="Stopper chưa đúng trạng thái",
                )

                buffer.robot_confirm_receive_magazine()
                handle_tranfer_magazine(
                    destination, line, destination_type, floor, "destination"
                )

                process_handler.mission.pop(0)
                logging.info(f"Mission remainning: {process_handler.mission}")
                if not process_handler.mission:
                    handle_robot_movement(
                        STANDBY_LOCATION,
                        "Robot chưa hoàn thành di chuyển tới vị trí standby",
                    )
                    process_handler.control_folk_conveyor(50)
                    process_handler.control_led("yellow")

            time.sleep(1)
        except Exception as e:
            logging.error(f"Lỗi trong quá trình thực thi nhiệm vụ: {str(e)}")


def check_send_message():
    while not stop_threads:
        target_ip = LINE_CONFIG.get(("line 28", "unloader", 1), {}).get("address")
        target = socket_server.get_client_socket_by_ip(target_ip)
        if target:
            process_handler.send_message_to_call(target, "line 28", "unloader", 1)
        time.sleep(5)


if __name__ == "__main__":
    try:
        logging.info("Đang khởi động server...")
        server = socket_server

        mission_create_thread = threading.Thread(target=handle_mission_creation)
        mission_create_thread.daemon = True

        monitor_thread = threading.Thread(target=monitor_data)
        monitor_thread.daemon = True

        mission_create_thread.start()
        monitor_thread.start()

        send_check_thread = threading.Thread(target=check_send_message)
        send_check_thread.daemon = True
        # send_check_thread.start()

        server.start()

    except KeyboardInterrupt:
        logging.info("\nĐang dừng server...")
        stop_threads = True
        server.stop()
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        stop_threads = True
        server.stop()

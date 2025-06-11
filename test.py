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
    APP_HOST,
    APP_PORT,
)
from process_handle import ProccessHandler
import buffer
import uvicorn
import state


def run_app():
    from api_app import app

    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")


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


def wait_for_condition(
    condition_func, timeout=600, interval=1, error_message="", check_func=None
):
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
        if check_func:
            check_func()

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
            check_func=check_pause_cancel,
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
            check_func=check_pause_cancel,
        )

        stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "stopper_action"
        )
        process_handler.control_robot_stopper(stopper_action, "open")
        wait_for_condition(
            lambda: process_handler.check_stopper_robot(stopper_action, "open"),
            error_message="Stopper chưa đúng trạng thái",
            check_func=check_pause_cancel,
        )

        direction = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "conveyor_direction"
        )
        process_handler.control_robot_conveyor(direction)
        wait_for_condition(
            lambda: process_handler.check_conveyor_robot(direction),
            error_message="Chưa hoàn thành điều khiển băng tải",
            check_func=check_pause_cancel,
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
                    check_func=check_pause_cancel,
                )
        elif type == "destination":
            time.sleep(9)
            wait_for_condition(
                lambda: not (
                    process_handler.check_sensor_right_robot()
                    or process_handler.check_sensor_left_robot()
                ),
                error_message="Chưa hoàn thành trả hàng",
                check_func=check_pause_cancel,
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
            check_func=check_pause_cancel,
        )

        stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
            "stopper_action"
        )
        process_handler.control_robot_stopper(stopper_action, "close")
        wait_for_condition(
            lambda: process_handler.check_stopper_robot(stopper_action, "close"),
            error_message="Stopper chưa đúng trạng thái",
            check_func=check_pause_cancel,
        )

        process_handler.control_folk_conveyor(50)
        process_handler.send_message_to_call(target, line, machine_type, 0)

    except Exception as e:
        logging.error(f"Lỗi trong quá trình chuyển magazine: {str(e)}")
        raise
        # handle_exception_mission(e)
        # handle_tranfer_magazine(location, line, machine_type, floor, type)


def handle_mission_creation():
    """Xử lý tạo nhiệm vụ"""
    while not stop_threads:
        try:
            mission_data = socket_server.get_mission_data()
            for mission in mission_data:
                process_handler.create_mission(mission)
            time.sleep(1)
        except Exception as e:
            logging.error(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")


def monitor_data():
    """Giám sát và xử lý dữ liệu"""
    while not stop_threads:
        try:
            check_pause_cancel()

            if process_handler.mission:
                logging.info(f"Danh sách nhiệm vụ: {process_handler.mission}")
                mission = process_handler.mission[0]

                pick_up = mission["pick_up"]
                destination = mission["destination"]
                floor = mission["floor"]
                line = mission["line"]
                machine_type = mission["machine_type"]

                if not process_handler.is_line_auto(line.replace(" ", "").lower()):
                    time.sleep(1)
                    return

                state.magazine_status = {"mission": line, "floor": floor}

                pick_up_type = "unloader" if machine_type == "loader" else "loader"
                destination_type = machine_type

                state.robot_status = False

                handle_tranfer_magazine(pick_up, line, pick_up_type, floor, "pickup")

                handle_robot_movement(
                    BUFFER_LOCATION, "Robot chưa hoàn thành di chuyển tới buffer"
                )

                process_handler.control_folk_conveyor(HEIGHT_BUFFER)
                wait_for_condition(
                    lambda: process_handler.check_lift_conveyor(HEIGHT_BUFFER),
                    error_message="Robot chưa đạt độ cao băng tải",
                    check_func=check_pause_cancel,
                )

                process_handler.control_robot_stopper("cw", "open")
                wait_for_condition(
                    lambda: process_handler.check_stopper_robot("cw", "open"),
                    error_message="Stopper chưa đúng trạng thái",
                    check_func=check_pause_cancel,
                )

                wait_for_condition(
                    lambda: buffer.buffer_allow_action(),
                    error_message="Buffer chưa sẵn sàng",
                    check_func=check_pause_cancel,
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
                    check_func=check_pause_cancel,
                )

                time.sleep(20)
                check_pause_cancel()

                process_handler.control_robot_conveyor("stop")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("stop"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                    check_func=check_pause_cancel,
                )

                wait_for_condition(
                    lambda: buffer.confirm_receive_magazine(),
                    error_message="Buffer chưa xử lý xong",
                    check_func=check_pause_cancel,
                )

                process_handler.control_robot_conveyor("cw")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("cw"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                    check_func=check_pause_cancel,
                )

                buffer.robot_wanna_receive_magazine()
                wait_for_condition(
                    lambda: process_handler.check_sensor_left_robot(),
                    error_message="Chưa hoàn thành nhận hàng",
                    check_func=check_pause_cancel,
                )

                process_handler.control_robot_conveyor("stop")
                wait_for_condition(
                    lambda: process_handler.check_conveyor_robot("stop"),
                    error_message="Robot chưa hoàn thành điều khiển băng tải",
                    check_func=check_pause_cancel,
                )

                process_handler.control_robot_stopper("cw", "close")
                wait_for_condition(
                    lambda: process_handler.check_stopper_robot("cw", "close"),
                    error_message="Stopper chưa đúng trạng thái",
                    check_func=check_pause_cancel,
                )

                buffer.robot_confirm_receive_magazine()
                handle_tranfer_magazine(
                    destination, line, destination_type, floor, "destination"
                )

                server.remove_first_mission()
                process_handler.mission.pop(0)
                logging.info(f"Mission remainning: {process_handler.mission}")
                if not process_handler.mission:
                    robot_to_standby()

            time.sleep(1)
        except Exception as e:
            logging.error(f"Lỗi trong quá trình thực thi nhiệm vụ: {str(e)}")
            handle_exception_mission(e)


def handle_exception_mission(exception):
    if "Mission cancelled" in str(exception).lower():
        if process_handler.mission:
            try:
                process_handler.mission.pop(0)
                reset_status_robot()
                logging.info("Đã loại bỏ nhiệm vụ bị hủy.")
            except Exception as pop_err:
                logging.warning(f"Lỗi khi loại bỏ nhiệm vụ: {pop_err}")
        else:
            robot_to_standby()


def robot_to_standby():
    state.magazine_status = None
    state.robot_status = True
    process_handler.control_led("yellow")
    try:
        handle_robot_movement(
            STANDBY_LOCATION, "Robot chưa hoàn thành quay về standby."
        )
        reset_status_robot()
    except Exception as move_err:
        logging.warning(f"Lỗi khi đưa robot về standby: {move_err}")


def reset_status_robot():
    process_handler.control_folk_conveyor("stop")
    process_handler.control_folk_conveyor(50)
    process_handler.control_robot_stopper("all", "close")


def check_send_message():
    while not stop_threads:
        target_ip = LINE_CONFIG.get(("line 28", "unloader", 2), {}).get("address")
        target = socket_server.get_client_socket_by_ip(target_ip)
        # print(f"TARGET: {target}")
        if target:
            process_handler.send_message_to_call(target, "line 28", "unloader", 2)
        time.sleep(5)


def run_with_pause_cancel(target_func, *args, **kwargs):
    """
    Wrapper để thực thi target_func, tự động kiểm tra pause/cancel giữa các bước.
    target_func phải định kỳ gọi check_pause_cancel() ở các điểm an toàn.
    """
    try:
        while state.pause_event.is_set():
            time.sleep(0.5)
        if state.cancel_event.is_set():
            print("Mission cancelled before start")
            process_handler.mission.pop(0)
            return
        return target_func(*args, **kwargs)
    except Exception as e:
        print(f"Mission interrupted: {e}")
        return


def check_pause_cancel():
    if state.cancel_event.is_set():
        logging.warning("Nhiệm vụ bị hủy.")
        state.cancel_event.clear()  # Reset để tránh xử lý lặp

        # Xóa nhiệm vụ hiện tại nếu còn
        if process_handler.mission:
            process_handler.mission.pop(0)
            reset_status_robot()
            print(f"Mission after cancel: {process_handler.mission}")
            logging.info("Đã loại bỏ nhiệm vụ hiện tại khỏi danh sách.")

        raise Exception("Mission cancelled")

    while state.pause_event.is_set():
        logging.info("Robot đang tạm dừng...")
        time.sleep(0.5)

        # Nếu bị hủy trong lúc pause
        if state.cancel_event.is_set():
            logging.warning("Nhiệm vụ bị hủy trong khi đang tạm dừng.")
            state.cancel_event.clear()

            if process_handler.mission:
                process_handler.mission.pop(0)
                reset_status_robot()
                print(f"Mission after cancel: {process_handler.mission}")
                logging.info("Đã loại bỏ nhiệm vụ hiện tại khỏi danh sách.")

            raise Exception("Mission cancelled")


if __name__ == "__main__":
    try:
        logging.info("Đang khởi động server...")
        server = socket_server

        mission_create_thread = threading.Thread(target=handle_mission_creation)
        mission_create_thread.daemon = True

        monitor_thread = threading.Thread(
            target=run_with_pause_cancel, args=(monitor_data,)
        )
        monitor_thread.daemon = True

        app_thread = threading.Thread(target=run_app)
        app_thread.daemon = True

        mission_create_thread.start()
        monitor_thread.start()
        app_thread.start()

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

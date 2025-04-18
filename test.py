from socket_server import SocketServer

import time
import threading
import json
from config import (
    HEIGHT_BUFFER,
    BUFFER_LOCATION,
    LINE_CONFIG,
    STANDBY_LOCATION,
    CHARGE_LOCATION,
)
from process_handle import ProccessHandler
import buffer

socket_server = SocketServer()
stop_threads = False
process_handler = ProccessHandler()


def handle_tranfer_magazine(location, line, machine_type, floor, type):
    process_handler.control_robot_to_location(location)
    print(f"Robot dang di chuyen toi {location}")
    process_handler.control_led("green")
    while not process_handler.check_location_robot(location):
        print(f"Robot chua hoan thanh di chuyen toi {location}")
        time.sleep(6)
    height = LINE_CONFIG.get((line, machine_type, floor), {}).get("line_height")
    process_handler.control_folk_conveyor(height)
    while not process_handler.check_lift_conveyor(height):
        print("Robot chua dat do cao bang tai")
    stopper_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
        "stopper_action"
    )
    process_handler.control_robot_stopper(stopper_action, "open")
    while not process_handler.check_stopper_robot(stopper_action, "open"):
        print("Stopper chua dung trang thai")
        # time.sleep(3)
    direction = LINE_CONFIG.get((line, machine_type, floor), {}).get(
        "conveyor_direction"
    )
    process_handler.control_robot_conveyor(direction)
    while not process_handler.check_conveyor_robot(direction):
        print("Chua hoan thanh dieu khien bang tai")
    target_ip = LINE_CONFIG.get((line, machine_type, floor), {}).get("address")
    # print("Target ID: ", target_ip)
    target = socket_server.get_client_socket_by_ip(target_ip)
    # print("Target: ", target)
    # process_handler.send_message_to_call(target, line, machine_type, floor)
    sensor_check = LINE_CONFIG.get((line, machine_type, floor), {}).get("sensor_check")
    if type == "pickup":
        if sensor_check == "right":
            while not process_handler.check_sensor_right_robot():
                print("Chua hoan thanh nhan hang")
                # time.sleep(1)
        elif sensor_check == "left":
            while not process_handler.check_sensor_left_robot():
                print("Chua hoan thanh nhan hang")
                # time.sleep(1)
    if type == "destination":
        time.sleep(9)
        while (
            process_handler.check_sensor_right_robot()
            or process_handler.check_sensor_left_robot()
        ):
            print("Chua hoan thanh tra hang")
            time.sleep(6)
    process_handler.control_robot_conveyor("stop")
    while not process_handler.check_conveyor_robot("stop"):
        print("Chua hoan thanh dieu khien bang tai")
        # time.sleep(6)
    process_handler.control_robot_stopper(stopper_action, "close")
    while not process_handler.check_stopper_robot(stopper_action, "close"):
        print("Stopper chua dung trang thai")
        # time.sleep(3)
    process_handler.control_folk_conveyor(50)
    # process_handler.send_message_to_call(target, line, machine_type, 0)


def handle_mission_creation():
    while not stop_threads:
        try:
            mission_data = socket_server.get_mission_data()
            if mission_data:
                process_handler.create_mission(mission_data)
            time.sleep(1)
        except Exception as e:
            print(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")


def monitor_data():
    """Giám sát và hiển thị dữ liệu nhận được từ server"""
    while not stop_threads:
        # data = socket_server.get_mission_data()
        # while not data:
        #     print("Data is Empty")
        #     data = socket_server.get_mission_data()
        #     time.sleep(3)
        # print("Data: ", data)
        # data = {"line" : "line 25", "floor" : 1, "machine_type" : "loader"}
        # process_handler.create_mission(data)
        # list_mission = process_handler.mission
        # for mission in list_mission:
        try:
            if process_handler.mission:
                # data = {"line" : "line 25", "floor" : 1, "machine_type" : "loader"}
                # process_handler.create_mission(data)
                # list_mission = process_handler.mission
                # for mission in list_mission:
                print(f"Danh sach nhiem vu: {process_handler.mission}")
                mission = process_handler.mission[0]
                pick_up = mission["pick_up"]
                destination = mission["destination"]
                floor = mission["floor"]
                line = mission["line"]
                machine_type = mission["machine_type"]
                if machine_type == "loader":
                    pick_up_type = "unloader"
                    destination_type = machine_type
                elif machine_type == "unloader":
                    pick_up_type = "loader"
                    destination_type = machine_type
                handle_tranfer_magazine(pick_up, line, pick_up_type, floor, "pickup")
                process_handler.control_robot_to_location(BUFFER_LOCATION)
                print("Robot dang di chuyen toi pickup")
                while not process_handler.check_location_robot(BUFFER_LOCATION):
                    print("Robot chua hoan thanh di chuyen toi buffer")
                    # time.sleep(3)
                process_handler.control_folk_conveyor(HEIGHT_BUFFER)
                while not process_handler.check_lift_conveyor(HEIGHT_BUFFER):
                    print("Robot chua dat do cao bang tai")
                    # time.sleep(3)
                process_handler.control_robot_stopper("cw", "open")
                while not process_handler.check_stopper_robot("cw", "open"):
                    print("Stopper chua dung trang thai")
                    # time.sleep(3)
                while not buffer.buffer_allow_action():
                    print("Buffer chua san sang")
                buffer_route = LINE_CONFIG.get((line, destination_type, floor), {}).get(
                    "buffer_turn"
                )
                # print("Buffer route: ", buffer_route)
                buffer.buffer_turn(buffer_route)
                buffer_action = LINE_CONFIG.get(
                    (line, destination_type, floor), {}
                ).get("buffer_action")
                buffer.buffer_action(buffer_action)
                process_handler.control_robot_conveyor("ccw")
                while not process_handler.check_conveyor_robot("ccw"):
                    print("Robot chua hoan thanh dieu khien bang tai")
                    # time.sleep(2)
                time.sleep(20)
                process_handler.control_robot_conveyor("stop")
                while not process_handler.check_conveyor_robot("stop"):
                    print("Robot chua hoan thanh dieu khien bang tai")
                    # time.sleep(3)
                while not buffer.confirm_receive_magazine():
                    print("Buffer chua xu ly xong")
                    # time.sleep(2)
                process_handler.control_robot_conveyor("cw")
                while not process_handler.check_conveyor_robot("cw"):
                    print("Robot chua hoan thanh dieu khien bang tai")
                    # time.sleep(3)
                buffer.robot_wanna_receive_magazine()
                while not process_handler.check_sensor_left_robot():
                    print("Chua hoan thanh nhan hang")
                    # time.sleep(1)
                process_handler.control_robot_conveyor("stop")
                while not process_handler.check_conveyor_robot("stop"):
                    print("Robot chua hoan thanh dieu khien bang tai")
                    # time.sleep(3)
                process_handler.control_robot_stopper("cw", "close")
                while not process_handler.check_stopper_robot("cw", "close"):
                    print("Stopper chua dung trang thai")
                    # time.sleep(3)
                buffer.robot_confirm_receive_magazine()
                handle_tranfer_magazine(
                    destination, line, destination_type, floor, "destination"
                )
                process_handler.mission.pop(0)
                if not process_handler.mission:
                    process_handler.control_robot_to_location(STANDBY_LOCATION)
                    process_handler.control_folk_conveyor(50)
                    process_handler.control_led("yellow")
            time.sleep(1)
        except Exception as e:
            print(f"Lỗi trong quá trình thực thi nhiệm vụ: {str(e)}")


if __name__ == "__main__":
    # Khởi tạo server
    server = socket_server

    # status = process_handler.get_data_status_robot()["battery_level"]
    # print("Battery level: ", status)

    mission_create_thread = threading.Thread(target=handle_mission_creation, args=())

    mission_create_thread.start()

    # Tạo và khởi động thread giám sát dữ liệu
    monitor_thread = threading.Thread(target=monitor_data, args=())
    # monitor_thread.daemon = (
    #     True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
    # )
    monitor_thread.start()

    try:
        # Khởi động server
        print("Đang khởi động server...")
        server.start()
    except KeyboardInterrupt:
        # Xử lý khi người dùng nhấn Ctrl+C
        print("\nĐang dừng server...")
        server.stop()
    except Exception as e:
        print(f"Lỗi: {e}")
        server.stop()

from socket_server import SocketServer

import time
import threading
import json
from config import HEIGHT_BUFFER, BUFFER_LOCATION, LINE_CONFIG
from process_handle import ProccessHandler
import buffer

socket_server = SocketServer()
stop_threads = False
process_handler = ProccessHandler()


def handle_tranfer_magazine(location, line, machine_type, floor):
    process_handler.control_robot_to_location(location)
    print("Robot dang di chuyen toi pickup")
    while not process_handler.check_location_robot(location):
        print("Robot chua hoan thanh di chuyen toi pickup")
        time.sleep(3)
    height = LINE_CONFIG.get((line, machine_type, floor), {}).get("line_height")
    process_handler.control_folk_conveyor(height)
    while not process_handler.check_lift_conveyor(height):
        print("Robot chua dat do cao bang tai")
        # time.sleep(3)
    stopper_pu_action = LINE_CONFIG.get((line, machine_type, floor), {}).get(
        "stopper_action"
    )
    process_handler.control_robot_stopper(stopper_pu_action, "open")
    while not process_handler.check_stopper_robot(stopper_pu_action, "open"):
        print("Stopper chua dung trang thai")
        # time.sleep(3)
    if floor == 1:
        info_floor = [1, 0]
    elif floor == 2:
        info_floor = [0, 2]
    pu_direction = LINE_CONFIG.get((line, machine_type, floor), {}).get(
        "conveyor_direction"
    )
    process_handler.control_robot_conveyor(pu_direction)
    while not process_handler.check_conveyor_robot(pu_direction):
        print("Chua hoan thanh dieu khien bang tai")
        # time.sleep(6)
    process_handler.send_message_to_call(location, line, info_floor, machine_type)
    sensor_check = LINE_CONFIG.get((line, machine_type, floor), {}).get("sensor_check")
    if sensor_check == "right":
        while not process_handler.check_sensor_right_robot():
            print("Chua hoan thanh nhan hang")
            # time.sleep(6)
    elif sensor_check == "left":
        while not process_handler.check_sensor_left_robot():
            print("Chua hoan thanh nhan hang")
            # time.sleep(6)
    process_handler.control_robot_conveyor("stop")
    while not process_handler.check_conveyor_robot("stop"):
        print("Chua hoan thanh dieu khien bang tai")
        # time.sleep(6)
    process_handler.control_robot_stopper(stopper_pu_action, "close")
    while not process_handler.check_stopper_robot(stopper_pu_action, "close"):
        print("Stopper chua dung trang thai")
        # time.sleep(3)
    process_handler.send_message_to_call(location, line, [0, 0], machine_type)


def monitor_data():
    """Giám sát và hiển thị dữ liệu nhận được từ server"""
    while not stop_threads:
        # data = socket_server.get_mission_data()
        # while not data:
        #     print("Data is Empty")
        #     data = socket_server.get_mission_data()
        #     time.sleep(3)
        # print("Data: ", data)
        process_handler.create_mission()
        list_mission = process_handler.mission
        for mission in list_mission:
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
            handle_tranfer_magazine(pick_up, line, pick_up_type, floor)
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
            buffer_action = LINE_CONFIG.get((line, destination_type, floor), {}).get(
                "buffer_action"
            )
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
            process_handler.control_robot_conveyor("stop")
            while not process_handler.check_conveyor_robot("stop"):
                print("Robot chua hoan thanh dieu khien bang tai")
                # time.sleep(3)
            process_handler.control_robot_stopper("cw", "close")
            while not process_handler.check_stopper_robot("cw", "close"):
                print("Stopper chua dung trang thai")
                # time.sleep(3)
            buffer.robot_confirm_receive_magazine()
            handle_tranfer_magazine(destination, line, destination_type, floor)
            process_handler.control_robot_to_location("LM4")
            while not process_handler.check_location_robot("LM4"):
                print("Chua hoan thanh ve standby")
            # process_handler.control_robot_to_location()
            # Xây dựng thông điệp với giá trị trường là chuỗi bình thường mà không có dấu ngoặc kép thừa
            # message = {
            #     "line": i["line"],
            #     "floor": floor,
            #     "machine_type": i["machine_type"],
            # }

            # json_message = json.dumps(message)

            # Gửi thông điệp dưới dạng chuỗi JSON
            # server.broadcast_message(json_message)  # Gửi thông điệp dưới dạng chuỗi

        # time.sleep(3)  # Đợi 3 giây trước khi kiểm tra lại


if __name__ == "__main__":
    # Khởi tạo server
    # buffer.robot_confirm_receive_magazine()
    # buffer.confirm_transfer_magazine()
    # while True:
    #     print(process_handler.check_sensor_right_robot())
    #     time.sleep(3)
    server = socket_server

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

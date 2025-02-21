from socket_server import SocketServer

import time
import threading
import json
from config import MAP_LINE, HEIGHT_BUFFER, HEIGHT_FLOOR_2_LINE_25
from process_handle import ProccessHandler

socket_server = SocketServer()
stop_threads = False
process_handler = ProccessHandler()


def monitor_data():
    """Giám sát và hiển thị dữ liệu nhận được từ server"""
    while not stop_threads:
        data = socket_server.get_mission_data()
        process_handler.create_mission(data)
        list_mission = process_handler.mission
        for mission in list_mission:
            process_handler.control_robot_to_location(mission["pick_up"])
            print("Robot dang di chuyen toi pickup")
            while not process_handler.check_location_robot(mission["pick_up"]):
                print("Robot chua hoan thanh di chuyen toi pickup")
                time.sleep(6)
            # process_handler.control_folk_conveyor(400)
            # while not process_handler.check_lift_conveyor(400):
            #     print("Robot chua dat do cao bang tai")
            #     time.sleep(6)
            # process_handler.control_folk_conveyor(700)
            # while not process_handler.check_lift_conveyor(700):
            #     print("Robot chua dat do cao bang tai")
            #     time.sleep(6)
            process_handler.control_robot_stopper("cw","open")
            time.sleep(6)
            process_handler.control_robot_conveyor("cw")
            time.sleep(6)
            # while process_handler.check_sensor_robot() != "Sensor trai":
            #     print("Chua hoan thanh nhan hang")
            #     time.sleep(4)
            process_handler.control_robot_conveyor("stop")
            time.sleep(4)
            process_handler.control_robot_stopper("cw","close")
            time.sleep(4)
            process_handler.control_robot_to_location(mission["destination"])
            while not process_handler.check_location_robot(mission["destination"]):
                print("Robot chua hoan thanh di chuyen toi destination")
                time.sleep(6)
            

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

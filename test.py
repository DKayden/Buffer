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
        # print("data", data)

        line = data.get("line")
        floor = data.get("floor")
        machine_type = data.get("machine_type")
        # print(f"Line: {line}, Floor: {floor}, Machine type: {machine_type}")

        if line is not None:
            if line not in MAP_LINE:
                raise ValueError(f"Không tìm thấy thông tin cho line: {line}")

            station = MAP_LINE[line]
            pick_up, destination = (
                (station[0], station[1])
                if floor == 2
                else (station[1], station[0])
            )
            new_mission = {
                "pick_up": pick_up,
                "destination": destination,
                "floor": floor,
                "line": line,
                "machine_type": machine_type,
            }
            print(f"Nhiệm vụ mới : {new_mission}")
            # missions = []
            # for mission in missions:
            #     print(f"Mision: {mission}")
            #     if (
            #     mission["pick_up"] != new_mission["pick_up"]
            #     and mission["destination"] != new_mission["destination"]
            #     and mission["floor"] != new_mission["floor"]
            #     and mission["line"] != new_mission["line"]
            #     and mission["machine_type"] != new_mission["machine_type"]
            #     ):
            #         missions.append(new_mission)

            #     else:
            #         print("Đã tồn tại nhiệm vụ này")
            # new_mission = json.dumps(data_new_mission)
            # print(f"New Mission: {new_mission}")
            # print("Pickup: " ,{new_mission["pick_up"]})
            # print("Destination: ", {new_mission["destination"]})
            # process_handler.create_mission()
            # for mission in missions:
            print("Bắt đầu thực thi nhiệm vụ")
            process_handler.control_robot_to_location(new_mission["pick_up"])
            print("Robot dang di chuyen toi pickup")
            while not process_handler.check_location_robot(new_mission["pick_up"]):
                print("Robot chua hoan thanh di chuyen toi pickup")
            process_handler.control_folk_conveyor(400)
            time.sleep(6)
            process_handler.control_folk_conveyor(100)
            time.sleep(6)
            process_handler.control_robot_stopper("cw","open")
            time.sleep(6)
            process_handler.control_robot_conveyor("cw")
            time.sleep(6)
            process_handler.control_robot_conveyor("stop")
            time.sleep(4)
            process_handler.control_robot_stopper("cw","close")
            time.sleep(4)
            process_handler.control_robot_to_location(new_mission["destination"])
            while not process_handler.check_location_robot(new_mission["destination"]):
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

from socket_server import SocketServer

import time
import threading
import json
from config import MAP_LINE

socket_server = SocketServer()
stop_threads = False


def monitor_data(server):
    """Giám sát và hiển thị dữ liệu nhận được từ server"""
    while not stop_threads:
        data = socket_server.get_mission_data()
        print("data", data)

        line = data.get("line")
        floor = data.get("floor")
        machine_type = data.get("machine_type")
        print(f"Line: {line}, Floor: {floor}, Machine type: {machine_type}")

        if line is not None:
            if line not in MAP_LINE:
                raise ValueError(f"Không tìm thấy thông tin cho line: {line}")

            station = MAP_LINE[line]
            pick_up, destination = (
                (station[0], station[1])
                if floor == 2
                else (station[1], station[0])
            )
            print(f"Tạo nhiệm vụ từ {pick_up} đến {destination}")
            new_mission = {
                "pick_up": pick_up,
                "destination": destination,
                "floor": floor,
                "line": line,
                "machine_type": machine_type,
            }
                # Xây dựng thông điệp với giá trị trường là chuỗi bình thường mà không có dấu ngoặc kép thừa
                # message = {
                #     "line": i["line"],
                #     "floor": floor,
                #     "machine_type": i["machine_type"],
                # }

                # json_message = json.dumps(message)

                # Gửi thông điệp dưới dạng chuỗi JSON
                # server.broadcast_message(json_message)  # Gửi thông điệp dưới dạng chuỗi

        time.sleep(3)  # Đợi 3 giây trước khi kiểm tra lại


if __name__ == "__main__":
    # Khởi tạo server
    server = socket_server

    # Tạo và khởi động thread giám sát dữ liệu
    monitor_thread = threading.Thread(target=monitor_data, args=(server,))
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

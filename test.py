from process_handle import socket_server

# from icecream import ic
import time
import threading
import json


def monitor_data(server):
    """Giám sát và hiển thị dữ liệu nhận được từ server"""
    while True:
        data = server.get_received_data()
        if data:
            # ic("Dữ liệu hiện tại:", data)
            for i in data:
                # ic(i)
                if i["floor"][0] != 0:
                    floor = i["floor"][0]
                elif i["floor"][1] != 0:
                    floor = i["floor"][1]

                # Xây dựng thông điệp với giá trị trường là chuỗi bình thường mà không có dấu ngoặc kép thừa
                message = {
                    "line": i["line"],
                    "floor": floor,
                    "machine_type": i["machine_type"],
                }

                json_message = json.dumps(message)

                # Gửi thông điệp dưới dạng chuỗi JSON
                server.broadcast_message(json_message)  # Gửi thông điệp dưới dạng chuỗi

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
# Nha may
# from socket_server import SocketServer

# # from icecream import ic
# import time
# import threading
# import json

# socket_server = SocketServer()


# def monitor_data(server):
#     """Giám sát và hiển thị dữ liệu nhận được từ server"""
#     while True:
#         data = socket_server.get_received_data()
#         print("data", data)
#         if len(data):
#             for value in data:
#                 print("value", value)
#                 mission_data = value
#                 print("line: ", mission_data.get("line"))

#         # print("type", type(data))
#         # if data:
#         #     reception_data = json.loads(data[0])
#         #     print("reception_data" + reception_data)
#         # print("floor show:", (reception_data["floor"]))

#         # for i in data:
#         # print("i" + i[0])
#         # if i["floor"][0] != 0:
#         #     floor = i["floor"][0]
#         # elif i["floor"][1] != 0:
#         #     floor = i["floor"][1]

#         # Xây dựng thông điệp với giá trị trường là chuỗi bình thường mà không có dấu ngoặc kép thừa
#         # message = {
#         #     "line": i["line"],
#         #     "floor": floor,
#         #     "machine_type": i["machine_type"],
#         # }

#         # json_message = json.dumps(message)

#         # Gửi thông điệp dưới dạng chuỗi JSON
#         # server.broadcast_message(json_message)  # Gửi thông điệp dưới dạng chuỗi

#         time.sleep(3)  # Đợi 3 giây trước khi kiểm tra lại


# if __name__ == "__main__":
#     # Khởi tạo server
#     server = socket_server

#     # Tạo và khởi động thread giám sát dữ liệu
#     monitor_thread = threading.Thread(target=monitor_data, args=(server,))
#     # monitor_thread.daemon = (
#     #     True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
#     # )
#     monitor_thread.start()

#     try:
#         # Khởi động server
#         print("Đang khởi động server...")
#         server.start()
#     except KeyboardInterrupt:
#         # Xử lý khi người dùng nhấn Ctrl+C
#         print("\nĐang dừng server...")
#         server.stop()
#     except Exception as e:
#         print(f"Lỗi: {e}")
#         server.stop()

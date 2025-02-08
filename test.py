from process_handle import socket_server
from icecream import ic
import time
import threading

def monitor_data(server):
    """Giám sát và hiển thị dữ liệu nhận được từ server"""
    while True:
        data = server.get_received_data()
        if data:
            ic("Dữ liệu hiện tại:", data)
        time.sleep(1)  # Đợi 1 giây trước khi kiểm tra lại

if __name__ == '__main__':
    # Khởi tạo server
    server = socket_server
    
    # Tạo và khởi động thread giám sát dữ liệu
    monitor_thread = threading.Thread(target=monitor_data, args=(server,))
    monitor_thread.daemon = True  # Thread sẽ tự động kết thúc khi chương trình chính kết thúc
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

        
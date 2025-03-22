import uvicorn
from config import APP_HOST, APP_PORT
from app import app
from threading import Thread
from process_handle import ProccessHandler, socket_server
from socket_server import SocketServer
import logging
import threading
import time
import signal
import sys


def run_app():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")


class MainApplication:
    def __init__(self):
        self.socket_server = SocketServer()
        self.process_handler = ProccessHandler()
        self.stop_flag = False

    def handle_mission_creation(self):
        """Liên tục kiểm tra và tạo nhiệm vụ mới từ dữ liệu socket server"""
        while not self.stop_flag:
            try:
                # Lấy dữ liệu nhiệm vụ từ socket server
                mission_data = self.socket_server.get_mission_data()
                if mission_data:
                    # Tạo nhiệm vụ mới từ dữ liệu nhận được
                    self.process_handler.create_mission(mission_data)
                time.sleep(1)  # Tránh CPU quá tải
            except Exception as e:
                print(f"Lỗi trong quá trình tạo nhiệm vụ: {str(e)}")

    def handle_mission_execution(self):
        """Liên tục kiểm tra và thực thi các nhiệm vụ trong danh sách"""
        while not self.stop_flag:
            try:
                if self.process_handler.mission:
                    # Xử lý nhiệm vụ theo logic trong monitor_data
                    mission = self.process_handler.mission[0]
                    pick_up = mission["pick_up"]
                    destination = mission["destination"]
                    floor = mission["floor"]
                    line = mission["line"]
                    machine_type = mission["machine_type"]

                    if machine_type == "loader":
                        pick_up_type = "unloader"
                        destination_type = machine_type
                    elif machine_type == "unloader":
                        pick_up_type = machine_type
                        destination_type = "loader"

                    # Thực hiện các bước xử lý nhiệm vụ
                    self.process_handler.process_handle_tranfer_goods(
                        floor=floor,
                        direction="cw",  # Hướng mặc định, cần điều chỉnh theo logic thực tế
                        location=pick_up,
                        type="pickup",
                        line=line,
                        machine_type=pick_up_type,
                    )

                    self.process_handler.process_handle_tranfer_goods(
                        floor=floor,
                        direction="ccw",  # Hướng mặc định, cần điều chỉnh theo logic thực tế
                        location=destination,
                        type="destination",
                        line=line,
                        machine_type=destination_type,
                    )

                    # Xóa nhiệm vụ đã hoàn thành
                    self.process_handler.mission.pop(0)
                time.sleep(1)  # Tránh CPU quá tải
            except Exception as e:
                print(f"Lỗi trong quá trình thực thi nhiệm vụ: {str(e)}")

    def signal_handler(self, signum, frame):
        """Xử lý tín hiệu dừng chương trình"""
        print("\nĐang dừng chương trình...")
        self.stop_flag = True
        self.socket_server.stop()
        sys.exit(0)

    def run(self):
        """Khởi chạy ứng dụng"""
        try:
            # Đăng ký handler xử lý tín hiệu Ctrl+C
            signal.signal(signal.SIGINT, self.signal_handler)

            # Tạo và khởi động các thread
            mission_creation_thread = threading.Thread(
                target=self.handle_mission_creation
            )
            mission_execution_thread = threading.Thread(
                target=self.handle_mission_execution
            )

            mission_creation_thread.daemon = True
            mission_execution_thread.daemon = True

            mission_creation_thread.start()
            mission_execution_thread.start()

            # Khởi động socket server
            print("Đang khởi động server...")
            self.socket_server.start()

        except Exception as e:
            print(f"Lỗi khi khởi động ứng dụng: {str(e)}")
            self.socket_server.stop()
            sys.exit(1)


if __name__ == "__main__":
    app = MainApplication()
    app.run()

import uvicorn
from config import (
    APP_HOST,
    APP_PORT,
    BUFFER_LOCATION,
    LINE_CONFIG,
    HEIGHT_BUFFER,
    STANDBY_LOCATION,
)
from app import app
from threading import Thread
from process_handle import ProccessHandler, socket_server
from socket_server import SocketServer
import logging
import threading
import time
import signal
import sys
import buffer


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
                        # destination_type = machine_type
                    elif machine_type == "unloader":
                        pick_up_type = "loader"
                    destination_type = machine_type

                    # Thực hiện các bước xử lý nhiệm vụ
                    self.process_handler.process_handle_tranfer_goods(
                        pick_up, line, pick_up_type, floor, "pickup"
                    )

                    self.process_handler.control_robot_to_location(BUFFER_LOCATION)
                    print("Robot dang di chuyen toi pickup")
                    while not self.process_handler.check_location_robot(
                        BUFFER_LOCATION
                    ):
                        print("Robot chua hoan thanh di chuyen toi buffer")
                        # time.sleep(3)
                    self.process_handler.control_folk_conveyor(HEIGHT_BUFFER)
                    while not self.process_handler.check_lift_conveyor(HEIGHT_BUFFER):
                        print("Robot chua dat do cao bang tai")
                        # time.sleep(3)
                    self.process_handler.control_robot_stopper("cw", "open")
                    while not self.process_handler.check_stopper_robot("cw", "open"):
                        print("Stopper chua dung trang thai")
                        # time.sleep(3)
                    while not buffer.buffer_allow_action():
                        print("Buffer chua san sang")
                    buffer_action = LINE_CONFIG.get(
                        (line, destination_type, floor), {}
                    ).get("buffer_action")
                    buffer.buffer_action(buffer_action)
                    self.process_handler.control_robot_conveyor("ccw")
                    while not self.process_handler.check_conveyor_robot("ccw"):
                        print("Robot chua hoan thanh dieu khien bang tai")
                        # time.sleep(2)
                    time.sleep(20)
                    self.process_handler.control_robot_conveyor("stop")
                    while not self.process_handler.check_conveyor_robot("stop"):
                        print("Robot chua hoan thanh dieu khien bang tai")
                        # time.sleep(3)
                    while not buffer.confirm_receive_magazine():
                        print("Buffer chua xu ly xong")
                        # time.sleep(2)
                    self.process_handler.control_robot_conveyor("cw")
                    while not self.process_handler.check_conveyor_robot("cw"):
                        print("Robot chua hoan thanh dieu khien bang tai")
                        # time.sleep(3)
                    buffer.robot_wanna_receive_magazine()
                    while not self.process_handler.check_sensor_left_robot():
                        print("Chua hoan thanh nhan hang")
                    self.process_handler.control_robot_conveyor("stop")
                    while not self.process_handler.check_conveyor_robot("stop"):
                        print("Robot chua hoan thanh dieu khien bang tai")
                        # time.sleep(3)
                    self.process_handler.control_robot_stopper("cw", "close")
                    while not self.process_handler.check_stopper_robot("cw", "close"):
                        print("Stopper chua dung trang thai")
                        # time.sleep(3)
                    buffer.robot_confirm_receive_magazine()

                    self.process_handler.process_handle_tranfer_goods(
                        destination, line, destination_type, floor, "destination"
                    )

                    # Xóa nhiệm vụ đã hoàn thành
                    self.process_handler.mission.pop(0)

                    self.process_handler.control_robot_to_location(STANDBY_LOCATION)
                    while not self.process_handler.check_location_robot(
                        STANDBY_LOCATION
                    ):
                        print("Chua hoan thanh ve standby")
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
    # app = MainApplication()
    # app.run()
    run_app()

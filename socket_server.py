import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Any
import json
from config import SOCKET_HOST, SOCKET_PORT, MAP_ADDRESS
import state
import logging
import time
import random

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class SocketServer:
    def __init__(
        self, host: str = SOCKET_HOST, port: int = SOCKET_PORT, max_workers: int = 10
    ):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.client_info = {}
        self.clients: List[socket.socket] = []
        self.received_data: List[Any] = []
        self.receive_dict_value = {}

        self._lock = threading.Lock()
        self.mission_lock = threading.Lock()
        self.mission_history = set()
        self.mission_data = {"missions": []}
        self._init_call_status()

        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        self.previous_call_status = {}
        self.monitoring_thread = None
        self.stop_monitoring = False

    def _init_call_status(self):
        lines = ["line25", "line26", "line27", "line28"]
        machine_types = ["loader", "unloader"]

        for line in lines:
            for machine_type in machine_types:
                # Key cho floor (không có suffix)
                key = f"call_{machine_type}_{line}"
                state.call_status[key] = 0

                # Key cho floor 1 và 2 (có suffix)
                for floor_suffix in ["_1", "_2"]:
                    key = f"call_{machine_type}_{line}{floor_suffix}"
                    state.call_status[key] = 0

    def random_sleep(self, min_seconds: float = 1.0, max_seconds: float = 10.0):
        """
        Thực hiện sleep ngẫu nhiên trong khoảng thời gian từ min_seconds đến max_seconds

        Args:
            min_seconds (float): Thời gian tối thiểu (mặc định: 1.0 giây)
            max_seconds (float): Thời gian tối đa (mặc định: 10.0 giây)
        """
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)

    def start_signal_monitoring(self):
        """Bắt đầu thread giám sát tín hiệu liên tục"""
        self.monitoring_thread = threading.Thread(
            target=self._monitor_signals, daemon=True
        )
        self.monitoring_thread.start()
        print("Đã bắt đầu giám sát tín hiệu loader/unloader")

    def _monitor_signals(self):
        """Giám sát tín hiệu liên tục và hủy nhiệm vụ khi cần"""
        while not self.stop_monitoring:
            try:
                with self._lock:
                    current_status = state.call_status.copy()

                # Kiểm tra các cặp loader/unloader
                for line_num in ["25", "26", "27", "28"]:
                    for floor_suffix in ["", "_1", "_2"]:
                        loader_key = f"call_loader_line{line_num}{floor_suffix}"
                        unloader_key = f"call_unloader_line{line_num}{floor_suffix}"

                        # Chỉ kiểm tra nếu cả hai key đều tồn tại
                        if (
                            loader_key in current_status
                            and unloader_key in current_status
                        ):
                            loader_current = current_status[loader_key]
                            unloader_current = current_status[unloader_key]

                            # Lấy trạng thái trước đó
                            loader_previous = self.previous_call_status.get(
                                loader_key, 0
                            )
                            unloader_previous = self.previous_call_status.get(
                                unloader_key, 0
                            )

                            # Nếu có tín hiệu chuyển từ 1 về 0
                            if (loader_previous == 1 and loader_current == 0) or (
                                unloader_previous == 1 and unloader_current == 0
                            ):
                                logging.info(
                                    f"Phát hiện tín hiệu chuyển về 0: {loader_key}={loader_current}, {unloader_key}={unloader_current}"
                                )
                                logging.info(
                                    f"Trạng thái trước: {loader_key}={loader_previous}, {unloader_key}={unloader_previous}"
                                )
                                self._cancel_related_missions(line_num, floor_suffix)

                # Cập nhật trạng thái trước đó
                self.previous_call_status = current_status.copy()

                time.sleep(1)  # Kiểm tra mỗi giây

            except Exception as e:
                print(f"Lỗi trong quá trình giám sát tín hiệu: {e}")
                time.sleep(1)

    def _cancel_related_missions(self, line_num, floor_suffix):
        """Hủy các nhiệm vụ liên quan đến line và floor cụ thể"""
        try:
            with self.mission_lock:
                missions_to_remove = []

                for i, mission in enumerate(self.mission_data["missions"]):
                    mission_line = mission.get("line", "").replace(" ", "").lower()
                    mission_floor = mission.get("floor", 0)

                    # Xác định floor từ suffix
                    if floor_suffix == "" or floor_suffix == "_1":
                        target_floor = 1
                    else:  # floor_suffix == "_2"
                        target_floor = 2

                    # Kiểm tra xem nhiệm vụ có liên quan không
                    if (
                        f"line{line_num}" in mission_line
                        and mission_floor == target_floor
                    ):
                        missions_to_remove.append(i)
                        print(
                            f"Hủy nhiệm vụ liên quan: Line {line_num}, Floor {target_floor}, Type {mission.get('machine_type')}"
                        )

                # Xóa các nhiệm vụ từ cuối lên để tránh lỗi index
                for i in reversed(missions_to_remove):
                    removed_mission = self.mission_data["missions"].pop(i)
                    # Xóa khỏi lịch sử
                    key = (
                        removed_mission["floor"],
                        tuple(removed_mission["line"]),
                        removed_mission["machine_type"],
                    )
                    self.mission_history.discard(key)
                    print(f"Đã hủy nhiệm vụ: {removed_mission}")

        except Exception as e:
            print(f"Lỗi khi hủy nhiệm vụ: {e}")

    def start(self):
        """Khởi động server và lắng nghe kết nối"""
        max_retries = 5
        current_port = self.port

        for attempt in range(max_retries):
            try:
                self.server_socket.bind((self.host, current_port))
                self.server_socket.listen(5)
                logging.info(f"Server đang lắng nghe tại {self.host}:{current_port}")
                break
            except OSError as e:
                logging.info(f"Không thể sử dụng cổng {current_port}: {e}")
                current_port += 1
                if attempt == max_retries - 1:
                    raise ConnectionError(
                        f"Không thể tìm thấy cổng khả dụng sau {max_retries} lần thử"
                    )

        # self.start_signal_monitoring()

        while True:
            client_socket, address = self.server_socket.accept()
            self.clients.append(client_socket)
            logging.info(f"Kết nối mới từ {address}")
            self.executor.submit(self.handle_client, client_socket, address)

    def _update_call_status(self):
        for key in state.call_status:
            state.call_status[key] = 0

        for ip, info in self.receive_dict_value.items():
            line = info.get("line", "").replace(" ", "").lower()
            machine_type = info.get("machine_type", "").lower()
            floors = info.get("floor", [])

            for floor_index, floor_value in enumerate(floors):
                if floor_value != 0:
                    if floor_index == 0:
                        key = f"call_{machine_type}_{line}"
                    else:
                        key = f"call_{machine_type}_{line}_{floor_index}"

                    if key in state.call_status:
                        state.call_status[key] = 1

    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Xử lý dữ liệu từ một client cụ thể"""
        try:
            location_data = client_socket.recv(1024).decode("utf-8")
            self.client_info[client_socket] = {"location": location_data}

            while True:
                data = client_socket.recv(1024)
                time.sleep(10)
                # self.random_sleep()
                if not data:
                    break

                processed_data = json.loads(data.decode("utf-8"))

                with self._lock:
                    self.receive_dict_value[address[0]] = processed_data

                    self._update_call_status()

                    for ip1, ip2 in MAP_ADDRESS:
                        client1_data = self.receive_dict_value.get(ip1)
                        client2_data = self.receive_dict_value.get(ip2)

                        if not (client1_data and client2_data):
                            continue

                        floors1 = client1_data.get("floor")
                        floors2 = client2_data.get("floor")
                        lines1 = client1_data.get("line")

                        if not (floors1 and floors2 and lines1) or len(floors1) != len(
                            floors2
                        ):
                            continue

                        for floor_index, (f1, f2) in enumerate(zip(floors1, floors2)):
                            if f1 == f2 and f1 != 0:
                                machine_type = "loader" if f1 == 1 else "unloader"
                                mission_key = (f1, tuple(lines1), machine_type)

                                with self.mission_lock:
                                    if mission_key not in self.mission_history:
                                        mission_item = {
                                            "floor": f1,
                                            "line": lines1,
                                            "machine_type": machine_type,
                                        }
                                        self.mission_data["missions"].append(
                                            mission_item
                                        )
                                        self.mission_history.add(mission_key)
                                        logging.info(
                                            f"Mission được tạo: {mission_item}"
                                        )

        except Exception as e:
            logging.info(f"Lỗi khi xử lý client {address}: {e}")
            # pass
        finally:
            self._cleanup_client(client_socket, address)

    def _cleanup_client(self, client_socket, address):
        """Dọn dẹp khi kết thúc kết nối với client"""
        if client_socket in self.client_info:
            del self.client_info[client_socket]
        client_socket.close()
        self.clients.remove(client_socket)
        logging.info(f"Đã đóng kết nối từ {address}")

    def get_received_data(self) -> List[Any]:
        """Lấy dữ liệu đã nhận (deep copy)"""
        with self._lock:
            return self.received_data.copy()

    def get_mission_data(self):
        """Lấy danh sách nhiệm vụ hiện tại"""
        with self.mission_lock:
            return self.mission_data["missions"].copy()

    def clear_mission_data(self):
        """Xóa toàn bộ dữ liệu nhiệm vụ"""
        with self.mission_lock:
            self.mission_data["missions"].clear()
            self.mission_history.clear()

    def remove_first_mission(self):
        """Xoá nhiệm vụ đầu tiên và loại bỏ khỏi lịch sử"""
        with self.mission_lock:
            if self.mission_data["missions"]:
                mission = self.mission_data["missions"].pop(0)
                key = (
                    mission["floor"],
                    tuple(mission["line"]),
                    mission["machine_type"],
                )
                self.mission_history.discard(key)
                return mission
            return None

    def stop(self):
        """Dừng server và đóng các socket"""
        logging.info("Đang dừng server")
        # self.stop_monitoring_signals()
        for client in self.clients:
            client.close()
        self.server_socket.close()
        self.executor.shutdown(wait=True)
        logging.info("Server đã dừng")

    def get_client_socket_by_ip(self, target_ip):
        """Tìm socket client theo IP"""
        for client_socket in self.clients:
            try:
                client_ip = client_socket.getpeername()[0]
                if client_ip == target_ip:
                    return client_socket
            except Exception as e:
                logging.info(f"Lỗi khi lấy thông tin client: {e}")
        return None

    def broadcast_message(
        self, message: str, target_socket: socket.socket | None = None
    ):
        """Gửi tin nhắn tới tất cả hoặc một client cụ thể"""
        encoded_message = message.encode("utf-8")
        with self._lock:
            if target_socket:
                try:
                    target_socket.send(encoded_message)
                    logging.info(
                        f"Đã gửi tin nhắn đến {target_socket.getpeername()[0]}: {message}"
                    )
                except Exception as e:
                    logging.info(f"Lỗi khi gửi tin nhắn đến client cụ thể: {e}")
                    self.broadcast_message(message, target_socket)

            else:
                for client in self.clients:
                    try:
                        client.send(encoded_message)
                    except Exception as e:
                        logging.info(f"Lỗi khi gửi tin nhắn đến client: {e}")
                        continue
                logging.info(f"Đã gửi tin nhắn đến tất cả client: {message}")

    def stop_monitoring_signals(self):
        """Dừng thread giám sát tín hiệu"""
        self.stop_monitoring = True
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)

    def get_signal_status(self):
        """Lấy trạng thái tín hiệu hiện tại để debug"""
        with self._lock:
            return state.call_status.copy()

    def print_signal_status(self):
        """In trạng thái tín hiệu hiện tại"""
        current_status = self.get_signal_status()
        for key, value in current_status.items():
            if value == 1:  # Chỉ in các tín hiệu đang active
                print(f"{key}: {value}")

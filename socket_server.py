import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Any
import json
from config import SOCKET_HOST, SOCKET_PORT, MAP_ADDRESS


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
        self.received_data: List[Any] = []  # Danh sách lưu trữ dữ liệu
        self.receive_dict_value = {}
        self.mission_data = {}
        self._lock = threading.Lock()  # Lock để đồng bộ hóa truy cập vào received_data
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def start(self):
        """Khởi động server và lắng nghe kết nối"""
        max_retries = 5
        current_port = self.port

        for attempt in range(max_retries):
            try:
                self.server_socket.bind((self.host, current_port))
                self.server_socket.listen(5)
                print(f"Server đang lắng nghe tại {self.host}:{current_port}")
                break
            except OSError as e:
                print(f"Không thể sử dụng cổng {current_port}: {e}")
                current_port += 1
                if attempt == max_retries - 1:
                    raise ConnectionError(
                        f"Không thể tìm thấy cổng khả dụng sau {max_retries} lần thử"
                    )

        while True:
            client_socket, address = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"Kết nối mới từ {address}")
            self.executor.submit(self.handle_client, client_socket, address)

    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Xử lý dữ liệu từ một client cụ thể"""
        try:
            location_data = client_socket.recv(1024).decode("utf-8")
            self.client_info[client_socket] = {"location": location_data}

            while True:
                data = client_socket.recv(1024)
                if not data:
                    break

                processed_data = json.loads(data.decode("utf-8"))

                with self._lock:
                    dict_value = {address[0]: processed_data}
                    self.receive_dict_value.update(dict_value)
                    # json_receive_divt_value = json.dumps(self.receive_dict_value, ensure_ascii=False, indent=4)
                    print(f"Đã nhận dữ liệu {self.receive_dict_value}")
                    print(
                        "______________________________________________________________________________________________________________________________________________"
                    )

                    client1_data, client2_data = None, None
                    for pair in MAP_ADDRESS:
                        for key, value in self.receive_dict_value.items():
                            if key == pair[0]:
                                client1_data = value
                            elif key == pair[1]:
                                client2_data = value
                    if client1_data and client2_data:
                        if "floor" in client1_data and "floor" in client2_data:
                            for i in range(len(client1_data["floor"])):
                                if (
                                    client1_data["floor"][i] == client2_data["floor"][i]
                                    and client1_data["floor"][i] != 0
                                    and client2_data["floor"][i] != 0
                                ):
                                    machine_type = (
                                        "loader"
                                        if client1_data["floor"][i] == 1
                                        else "unloader"
                                    )
                                    mission_item = {
                                        "floor": client1_data["floor"][i],
                                        "line": client1_data["line"],
                                        "machine_type": machine_type,
                                    }
                                    self.mission_data.update(mission_item)
                    # print(f"Mission: {self.mission_data}")

        except Exception as e:
            print(f"Lỗi khi xử lý client {address}: {e}")
        finally:
            self._cleanup_client(client_socket, address)

    def _cleanup_client(self, client_socket, address):
        """Dọn dẹp khi kết thúc kết nối với client"""
        if client_socket in self.client_info:
            del self.client_info[client_socket]
        client_socket.close()
        self.clients.remove(client_socket)
        print(f"Đã đóng kết nối từ {address}")

    def get_received_data(self) -> List[Any]:
        """Phương thức để truy cập dữ liệu từ bên ngoài"""
        with self._lock:
            return self.received_data.copy()

    def get_mission_data(self):
        with self._lock:
            return self.mission_data.copy()

    def clear_mission_data(self):
        """Xóa toàn bộ dữ liệu đã nhận"""
        with self._lock:
            self.mission_data.clear()

    def remove_first_item_mission_data(self):
        """Xóa dữ liệu đầu tiên"""
        with self._lock:
            if self.mission_data:
                return self.mission_data.pop(0)
            return None

    def stop(self):
        """Dừng server và đóng các socket"""
        print("Đang dừng server")
        for client in self.clients:
            client.close()
        self.server_socket.close()
        self.executor.shutdown(wait=True)
        print("Server đã dừng")

    def get_client_socket_by_ip(self, target_ip):
        for client_socket in self.clients:
            try:
                client_ip = client_socket.getpeername()[0]
                if client_ip == target_ip:
                    return client_socket
            except Exception as e:
                print(f"Lỗi khi lấy thông tin client: {e}")
        return None

    def broadcast_message(self, message: str, target_socket: socket.socket = None):
        """
        Gửi tin nhắn đến một client cụ thể hoặc tất cả các client
        """
        encoded_message = message.encode("utf-8")
        with self._lock:  # Sử dụng lock để đảm bảo thread safety
            if target_socket:
                # Gửi tin nhắn đến một client cụ thể
                try:
                    target_socket.send(encoded_message)
                    print(
                        f"Đã gửi tin nhắn đến {target_socket.getpeername()[0]}: {message}"
                    )
                except Exception as e:
                    print(f"Lỗi khi gửi tin nhắn đến client cụ thể: {e}")
            else:
                # Gửi tin nhắn đến tất cả client
                for client in self.clients:
                    try:
                        client.send(encoded_message)
                    except Exception as e:
                        print(f"Lỗi khi gửi tin nhắn đến client: {e}")
                        continue  # Tiếp tục gửi tin nhắn đến client khác nếu gặp lỗi
                print(f"Đã gửi tin nhắn đến tất cả client: {message}")

import socket
import threading
from typing import List, Any
import json
from config import SOCKET_HOST, SOCKET_PORT, MAP_ADDRESS


class SocketServer:

    def __init__(self, host: str = SOCKET_HOST, port: int = SOCKET_PORT):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_info = {}
        self.clients: List[socket.socket] = []
        self.received_data: List[Any] = []  # Danh sách lưu trữ dữ liệu
        self.receive_dict_value = {}
        self.mission_data = set()
        self._lock = threading.Lock()  # Lock để đồng bộ hóa truy cập vào received_data

    def start(self):
        """Khởi động server và lắng nghe kết nối"""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server đang lắng nghe tại {self.host}:{self.port}")

        while True:
            client_socket, address = self.server_socket.accept()
            self.clients.append(client_socket)
            print(f"Kết nối mới từ {address}")

            # Tạo thread mới để xử lý client
            client_thread = threading.Thread(
                target=self.handle_client, args=(client_socket, address)
            )
            client_thread.start()

    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Xử lý dữ liệu từ một client cụ thể"""
        try:
            # Nhận thông tin location từ client khi kết nối
            location_data = client_socket.recv(1024).decode("utf-8")
            self.client_info[client_socket] = {"location": location_data}
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break

                # Xử lý dữ liệu nhận được (ví dụ: decode từ bytes)
                processed_data = json.loads(data.decode("utf-8"))

                # Lưu dữ liệu vào danh sách với thread safety
                # if processed_data["floor"][0] != 0 or processed_data["floor"][1] != 0:

                with self._lock:
                    # self.receive_set_value.add(processed_data)
                    # self.received_data.append(processed_data)
                    # self.receive_dict_value
                    dict_value = {
                        address[0] : processed_data
                    }
                    self.receive_dict_value.update(dict_value)
                    print(f"Đã nhận dữ liệu {self.receive_dict_value}")

                    client1_data = None
                    client2_data = None
                    for pair in MAP_ADDRESS:
                        for key, value in self.receive_dict_value.items():
                            if key == pair[0]:
                                client1_data = value
                            elif key == pair[1]:
                                client2_data = value
                    print(f"Client 1: {client1_data}")
                    print(f"Client 2: {client2_data}")
                    if client1_data is not None and client2_data is not None:
                        for i in len(client1_data["floor"]):
                            if client1_data["floor"][i] == client2_data["floor"][i]:
                                self.mission_data.add({
                                    "floor" : client1_data["floor"],
                                    "line" : client1_data["line"]
                                })
                    print(f"Mission: {self.mission_data}")
                # Gửi phản hồi cho client
                # response = {"line": processed_data["line"], "floor": 0}
                # client_socket.send(json.dumps(response).encode("utf-8"))

        except Exception as e:
            # print(f"Lỗi khi xử lý client {address}: {e}")
            pass
        finally:
            if client_socket in self.client_info:
                del self.client_info[client_socket]
            client_socket.close()
            self.clients.remove(client_socket)
            print(f"Đã đóng kết nối từ {address}")

    def get_received_data(self) -> List[Any]:
        """Phương thức để truy cập dữ liệu từ bên ngoài"""
        with self._lock:
            return self.received_data.copy()

    def clear_data(self):
        """Xóa toàn bộ dữ liệu đã nhận"""
        with self._lock:
            self.received_data.clear()

    def remove_first_item(self):
        """Xóa dữ liệu đầu tiên"""
        with self._lock:
            if self.received_data:
                return self.received_data.pop(0)
            return None

    def stop(self):
        """Dừng server và đóng các socket"""
        print("Đang dừng server")
        for client in self.clients:
            client.close()
        self.server_socket.close()
        print("Server đã dừng")

    def broadcast_message(self, message: str, target_socket: socket.socket = None):
        """
        Gửi tin nhắn đến một client cụ thể hoặc tất cả các client

        Args:
            message (str): Tin nhắn cần gửi
            target_socket (socket.socket, optional): Socket của client cụ thể.
                Nếu None, gửi cho tất cả client
        """
        encoded_message = message.encode("utf-8")

        with self._lock:  # Sử dụng lock để đảm bảo thread safety
            if target_socket:
                # Gửi tin nhắn đến một client cụ thể
                try:
                    target_socket.send(encoded_message)
                    print(f"Đã gửi tin nhắn đến client cụ thể: {message}")
                except Exception as e:
                    print(f"Lỗi khi gửi tin nhắn đến client: {e}")
            else:
                # Gửi tin nhắn đến tất cả client
                for client in self.clients:
                    try:
                        client.send(encoded_message)
                    except Exception as e:
                        print(f"Lỗi khi gửi tin nhắn đến client: {e}")
                        # self.clients.remove(client)
                        continue  # Thêm continue để tiếp tục vòng lặp
                print(f"Đã gửi tin nhắn đến tất cả client: {message}")


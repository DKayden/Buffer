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
        self._lock = threading.Lock()  # Lock để đồng bộ hóa truy cập vào received_data
        self.mission_data: List[Any] = [] # Thêm biến để lưu mission data

    def start(self):
        """Khởi động server và lắng nghe kết nối"""
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server đang lắng nghe tại {self.host}:{self.port}")

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
            self.client_info[client_socket] = {
                "location": location_data,
                "address" : address[0],
                "last_data" : None
                }
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break

                # Xử lý dữ liệu nhận được
                processed_data = json.loads(data.decode("utf-8"))

                if processed_data["floor"][0] != 0 or processed_data["floor"][1] != 0:
                    for i in len(processed_data["floor"]):
                        for received_data in self.received_data:
                            if (received_data["line"] != processed_data["line"] and
                                received_data["floor"][i] != processed_data['floor'][i] and
                                received_data["machine_type"] != processed_data["machine_type"]):
                                with self._lock:
                                    # Cập nhật dữ liệu mới cho client hiện tại
                                    self.client_info[client_socket]["last_data"] = processed_data
                                    self.received_data.append(processed_data)
                                    print(f"Đã nhận dữ liệu từ {address}: {processed_data}")
                                    # Kiểm tra và cập nhật mission_data
                                    self.check_and_update_mission()

                # Gửi phản hồi cho client
                # response = {"line": processed_data["line"], "floor": 0}
                # client_socket.send(json.dumps(response).encode("utf-8"))

        except Exception as e:
            print(f"Lỗi khi xử lý client {address}: {e}")
            # pass
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
        
    def _get_client_data_for_pair(self, pair):
        """Lấy dữ liệu của cặp client"""
        client1_data = None
        client2_data = None
        
        for client, info in self.client_info.items():
            if info["address"] == pair[0]:
                client1_data = info["last_data"]
            elif info["address"] == pair[1]:
                client2_data = info["last_data"]
                
        return client1_data, client2_data

    def _create_new_mission(self, client1_data, client2_data):
        """Kiểm tra tính hợp lệ của mission"""
        if client1_data is not None and client2_data is not None:
            for i in len(client1_data["floor"]):
                if client1_data["floor"][i] == client2_data["floor"][i]:
                    for mission in self.mission_data:
                        if (mission["floor"] != client1_data["floor"][i] and
                            mission["line"] != client1_data["line"] and
                            mission["machine_type"] != client1_data["machine_type"]):
                            self.mission_data.append({
                                "floor": client1_data["floor"][i],
                                "line": client1_data["line"],
                                "machine_type": client1_data["machine_type"]
                            })
                            print(f"Đã tạo một nhiệm vụ mới:Floor {client1_data["floor"][i]}, Line {client1_data["line"]}, Machine_type: {client1_data["machine_type"]}")

    def check_and_update_mission(self):
        """Kiểm tra và cập nhật mission_data dựa trên các cặp địa chỉ"""
        with self._lock:
            for pair in MAP_ADDRESS:
                client1_data, client2_data = self._get_client_data_for_pair(pair)
                
                self._create_new_mission(client1_data, client2_data)

    def get_mission_data(self) -> List[Any]:
        """Lấy danh sách mission_data"""
        with self._lock:
            return self.mission_data.copy()
    
    def clear_mission_data(self):
        """Xóa toàn bộ mission_data"""
        with self._lock:
            self.mission_data.clear()

    def remove_first_mission(self):
        """Xóa mission đầu tiên"""
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

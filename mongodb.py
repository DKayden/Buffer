from pymongo import MongoClient
from datetime import datetime, UTC
from typing import Dict, List, Optional

class BufferDatabase:
    def __init__(self,connection_string: str = "mongodb://localhost:27017/"):
        """
        Khởi tạo kết nối với MongoDB

        Args:
            connection_string (str, optional): Chuỗi kết nối MongoDB.
        """

        self.client = MongoClient(connection_string)
        self.database = self.client["robot_management"]
        self.tasks = self.database['robot_tasks']

        # Tạo index cho các trường thường được tìm kiếm.
        self.tasks.create_index([("pickup_line", 1)])
        self.tasks.create_index([("pickup_floor", 1)])
        self.tasks.create_index([("machine_type", 1)])
        self.tasks.create_index([("is_processed", 1)])

    def _generate_task_id(self, pickup_line: str, machine_type: str, created_at: datetime):
        """
        Tạo ID cho nhiệm vụ

        Args:
        pickup_line(str): Tên line lấy hàng
        machine_type(str): Loại máy lấy hàng
        created_at(datetime): Thời gian tạo
        """
        timestamp = created_at.strftime("%d%m%Y_%H%M%S")
        task_id = f"{pickup_line}_{machine_type}_{timestamp}"
        return task_id.replace(" ", "_")

    def create_task(self,
                    pickup_line: str,
                    pickup_floor: int,
                    machine_type: str):
        """
        Tạo một nhiệm vụ mới

        Args:
            pickup_line (str): Tên line lấy hàng
            pickup_floor (int): Tầng đón hàng
            machine_type (str): Loại máy tính

        Returns:
            str: ID của nhiệm vụ
        """
        timestamp = datetime.now(UTC)
        task_id = self._generate_task_id(pickup_line, machine_type, timestamp)

        task = {
            "_id": task_id,
            "pickup_line": pickup_line,
            "pickup_floor": pickup_floor,
            "machine_type": machine_type,
            "is_processed": False,
            "created_at": timestamp,
            "updated_at": timestamp
        }

        self.tasks.insert_one(task)
        return task_id
    
    def update_task_status(self, task_id: str, is_processed: bool):
        """
        Cập nhật trạng thái của nhiệm vụ

        Args:
            task_id (str): ID của nhiệm vụ
            is_processed (bool): Trạng thái đã xử lý hay chưa
        """
        result = self.tasks.update_one(
            {"_id" : task_id},
            {
                "$set" : {
                    "is_processed": is_processed,
                    "updated_at": datetime.now(UTC)
                }
            }
        )
        return result.modified_count > 0
    
    def get_task(self, task_id: str):
        """
        Lấy thông tin nhiệm vụ theo ID

        Args:
        task_id (str): ID của nhiệm vụ
        """
        return self.tasks.find_one({"_id": task_id})

    def get_unprocessed_task(self):
        """
        Lấy danh sách nhiệm vụ chưa xử lý
        """
        return list(self.tasks.find({"is_processed": False}))
from config import (
    TRANSFER_ADDRESS,
    GIVE_ADDRESS,
    ACTION_ADDRESS,
    CHECK_ADDRESS,
    TURN_ADDRESS,
)
from modbus_client import ModbusClient
from config import MODBUS_HOST, MODBUS_PORT, MODBUS_TYPE

modbus_client = ModbusClient(host=MODBUS_HOST, port=MODBUS_PORT, type=MODBUS_TYPE)


def confirm_transfer_magazine():
    return modbus_client.read_input_register(TRANSFER_ADDRESS, 1)[0]


def buffer_action(action):
    try:
        if action == "flip":
            modbus_client.write_register(ACTION_ADDRESS, 1)
            print("Buffer đã nhận lệnh lật")
        elif action == "circular":
            modbus_client.write_register(ACTION_ADDRESS, 2)
            print("Buffer đã nhận lệnh xoay")
        else:
            raise ValueError("Loại hành động không hợp lệ")
    except Exception as e:
        print(f"Lỗi khi thực hiện thao tác buffer: {e}")
        raise


def confirm_receive_magazine():
    return modbus_client.read_input_register(GIVE_ADDRESS, 1)[0] == 1


def robot_wanna_receive_magazine():
    modbus_client.write_register(GIVE_ADDRESS, 1)
    print("Đã gửi yêu cầu nhận hàng cho Buffer")


def robot_confirm_receive_magazine():
    modbus_client.write_register(GIVE_ADDRESS, 0)
    print("Robot xác nhận đã lấy magazine")


def buffer_allow_action():
    return modbus_client.read_input_register(CHECK_ADDRESS, 1)[0] == 0


def buffer_turn(direction):
    try:
        if direction == "clockwise":
            modbus_client.write_register(TURN_ADDRESS, 0)
            print("Buffer xoay thuận chiều")
        elif direction == "counterclockwise":
            modbus_client.write_register(TURN_ADDRESS, 1)
            print("Buffer xoay nghịch chiều")
        else:
            raise ValueError("Loại hành động không hợp lệ")
    except Exception as e:
        print(f"Lỗi khi thực hiện thao tác buffer: {e}")
        raise

from config import TRANSFER_ADDRESS, GIVE_ADDRESS, ACTION_ADDRESS, RECEIVE_ADDRESS
from modbus_client import ModbusClient
from config import MODBUS_HOST, MODBUS_PORT, MODBUS_TYPE

modbus_client = ModbusClient(host=MODBUS_HOST, port=MODBUS_PORT, type=MODBUS_TYPE)

def allow_transfer_magazine():
    return modbus_client.read_holding_registers(TRANSFER_ADDRESS, 1)[0] == 1

def confirm_transfer_magazine():
    return modbus_client.read_holding_registers(TRANSFER_ADDRESS, 1)[0] == 0
    
def confirm_receive_magazine():
    return modbus_client.read_holding_registers(GIVE_ADDRESS, 1)[0] == 1

def buffer_action(action):
    try:
        if action == "flip":
            modbus_client.write_register(ACTION_ADDRESS, 2)
            print("Buffer đã nhận lệnh lật")
        elif action == "circular":
            modbus_client.write_register(ACTION_ADDRESS, 1)
            print("Buffer đã nhận lệnh xoay")
        else:
            raise ValueError("Loại hành động không hợp lệ")
    except Exception as e:
        print(f"Lỗi khi thực hiện thao tác buffer: {e}")
        raise
    
def robot_wanna_receive_magazine():
    modbus_client.write_register(RECEIVE_ADDRESS, 0)
    print("Robot đang chờ để lấy magazine")

def robot_confirm_receive_magazine():
    modbus_client.write_register(RECEIVE_ADDRESS, 1)
    print("Robot xác nhận đã lấy magazine")

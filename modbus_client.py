from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from pymodbus.transaction import ModbusSocketFramer
import time

class ModbusClient:
    def __init__(self, host:str=None, port:int=0, type:str='tcp') -> None:
        self.mb_host = host
        self.mb_port = port
        if type == "tcp":
            self.mb_client= ModbusTcpClient(host=self.mb_host, port=self.mb_port, framer=ModbusSocketFramer)
        elif type == "rtu":
            self.mb_client = ModbusSerialClient(port='/dev/ttyUSB0', baudrate=115200, bytesize=8, parity='N', stopbits=1)
    
    def connect(self) -> bool:
        try:
            self.mb_client.connect()
            return True
        except Exception as e:
            print(f"Error connecting to Modbus server: {e}")
            return False
    
    def disconnect(self) -> bool:
        try:
            self.mb_client.close()
            return True
        except Exception as e:
            print(f"Error disconnecting from Modbus server: {e}")
            return False
    def reconnect(self):
        self.disconnect()
        while True:
            self.connect()
            if self.connect():
                print("Successfully reconnected to Modbus server")
                break
            else:
                print("Reconnection failed, retrying...")
                time.sleep(5)  # Wait 5 seconds before retrying
    
    def read_holding_registers(self, address: int, count: int) -> list:
        if not self.connect():
            return []
        try:
            result = self.mb_client.read_holding_registers(address, count, slave=1)
            return result.registers
        except Exception as e:
            print(f"Error reading holding registers: {e}")
            self.reconnect()
            return []
        
    def read_input_register(self, address: int, count: int) -> list:
        if not self.connect():
            return []
        try:
            result = self.mb_client.read_input_registers(address, count, slave=1)
            return result.registers
        except Exception as e:
            print(f"Error reading input registers: {e}")
            self.reconnect()
            return []
        
    def write_register(self, address: int, value: int) -> bool:
        if not self.connect():
            return False
        try:
            self.mb_client.write_register(address, value, slave=1)
            return True
        except Exception as e:
            print(f"Error writing input register: {e}")
            self.reconnect()
            return False
        
ACTION_ADDRESS = 0
TRANSFER_ADDRESS = 1
GIVE_ADDRESS = 2
CHECK_ADDRESS = 4
TURN_ADDRESS = 5

APP_HOST = "0.0.0.0"
APP_PORT = 8000

ROBOT_HOST = "192.168.1.104"
ROBOT_PORT = 8000

MODBUS_HOST = "localhost"
MODBUS_PORT = 502
MODBUS_TYPE = "rtu"

BUFFER_HOST = "localhost"
BUFFER_PORT = 5000

BUFFER_LOCATION = "LM200"
BUFFER_ACTION = "flip"

SOCKET_HOST = "192.168.1.100"
SOCKET_PORT = 5000

CALL_HOST = "0.0.0.0"
CALL_PORT = 5000

MAP_ADDRESS = [["192.168.1.27", "192.168.1.28"]]

MAP_LINE = {
    "line 25": ["LM252", "LM251"],
    "line 26": ["LM262", "LM261"],
    "line 27": ["LM272", "LM271"],
    "line 28": ["LM282", "LM281"],
}

HEIGHT_BUFFER = 56

LINE_CONFIG = {
    ("line 25", "loader", 1): {
        "line_height": 60,
        "buffer_action": "flip",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.27",
    },
    ("line 25", "loader", 2): {
        "line_height": 770,
        "buffer_action": "circular",
        "buffer_turn": "counterclockwise",
        "stopper_action": "cw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.27",
    },
    ("line 25", "unloader", 1): {
        "line_height": 10,
        "buffer_action": "flip",
        "buffer_turn": "clockwise",
        "stopper_action": "ccw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.28",
    },
    ("line 25", "unloader", 2): {
        "line_height": 720,
        "buffer_action": "circular",
        "buffer_turn": "clockwise",
        "stopper_action": "ccw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.28",
    },
    ("line 26", "loader", 1): {
        "line_height": 60,
        "buffer_action": "flip",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.29",
    },
    ("line 26", "loader", 2): {
        "line_height": 770,
        "buffer_action": "circular",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.29",
    },
    ("line 26", "unloader", 1): {
        "line_height": 10,
        "buffer_action": "flip",
        "buffer_turn": "counterclockwise",
        "stopper_action": "cw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.30",
    },
    ("line 26", "unloader", 2): {
        "line_height": 720,
        "buffer_action": "circular",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.30",
    },
    ("line 27", "loader", 1): {
        "line_height": 60,
        "buffer_action": "flip",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.31",
    },
    ("line 27", "loader", 2): {
        "line_height": 770,
        "buffer_action": "circular",
        "buffer_turn": "counterclockwise",
        "stopper_action": "cw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.31",
    },
    ("line 27", "unloader", 1): {
        "line_height": 10,
        "buffer_action": "flip",
        "buffer_turn": "clockwise",
        "stopper_action": "ccw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.32",
    },
    ("line 27", "unloader", 2): {
        "line_height": 720,
        "buffer_action": "circular",
        "buffer_turn": "clockwise",
        "stopper_action": "ccw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.32",
    },
    ("line 28", "loader", 1): {
        "line_height": 60,
        "buffer_action": "flip",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.33",
    },
    ("line 28", "loader", 2): {
        "line_height": 770,
        "buffer_action": "circular",
        "buffer_turn": "lockwise",
        "stopper_action": "cw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.33",
    },
    ("line 28", "unloader", 1): {
        "line_height": 10,
        "buffer_action": "flip",
        "buffer_turn": "counterclockwise",
        "stopper_action": "cw",
        "conveyor_direction": "cw",
        "sensor_check": "left",
        "address": "192.168.1.34",
    },
    ("line 28", "unloader", 2): {
        "line_height": 720,
        "buffer_action": "circular",
        "buffer_turn": "clockwise",
        "stopper_action": "cw",
        "conveyor_direction": "ccw",
        "sensor_check": "right",
        "address": "192.168.1.34",
    },
}

STANDBY_LOCATION = "LM100"
CHARGE_LOCATION = "LM10"

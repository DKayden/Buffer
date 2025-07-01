import threading

magazine_status = None
pause_event = threading.Event()
cancel_event = threading.Event()

call_status = {
    # Floor (không có suffix)
    "call_loader_line25": 0,
    "call_loader_line26": 0,
    "call_loader_line27": 0,
    "call_loader_line28": 0,
    "call_unloader_line25": 0,
    "call_unloader_line26": 0,
    "call_unloader_line27": 0,
    "call_unloader_line28": 0,
    
    # Floor 1 (có suffix _1)
    "call_loader_line25_1": 0,
    "call_loader_line26_1": 0,
    "call_loader_line27_1": 0,
    "call_loader_line28_1": 0,
    "call_unloader_line25_1": 0,
    "call_unloader_line26_1": 0,
    "call_unloader_line27_1": 0,
    "call_unloader_line28_1": 0,
    
    # Floor 2 (có suffix _2)
    "call_loader_line25_2": 0,
    "call_loader_line26_2": 0,
    "call_loader_line27_2": 0,
    "call_loader_line28_2": 0,
    "call_unloader_line25_2": 0,
    "call_unloader_line26_2": 0,
    "call_unloader_line27_2": 0,
    "call_unloader_line28_2": 0,
}

robot_status = True
mode = ""

line_auto_web = []

history = {
    "status": "",
    "type": "",
    "mission": "",
    "floor": 0,
}

data_status = {}
messenge = ""
mission = []

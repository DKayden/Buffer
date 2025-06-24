import threading

magazine_status = None
pause_event = threading.Event()
cancel_event = threading.Event()

call_status = {
    "call_loader_line25": 0,
    "call_loader_line26": 0,
    "call_loader_line27": 0,
    "call_loader_line28": 0,
    "call_unloader_line25": 0,
    "call_unloader_line26": 0,
    "call_unloader_line27": 0,
    "call_unloader_line28": 0,
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

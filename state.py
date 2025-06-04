import threading

magazine_status = None
pause_event = threading.Event()
cancel_event = threading.Event()

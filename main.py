import uvicorn
from config import APP_HOST, APP_PORT
from app import app
from threading import Thread
from process_handle import ProccessHandler
from socket_server import SocketServer

def run_app():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")

if __name__ == "__main__":

  app_thread = Thread(target=run_app)
  app_thread.start()

  socket_server = SocketServer()
  server_socket_thread = Thread(target=socket_server.start)
  server_socket_thread.start()

  mission_thread = Thread(target=ProccessHandler.create_mission)
  mission_thread.start()

  process_thread = Thread(target=ProccessHandler.handle_magazine_process)
  process_thread.start()
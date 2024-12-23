import uvicorn
from config import APP_HOST, APP_PORT
from app import app
from threading import Thread
from process_handle import ProccessHandler

def run_app():
    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")

if __name__ == "__main__":

  app_thread = Thread(target=run_app)
  app_thread.start()

  mission_thread = Thread(target=ProccessHandler.get_mission_from_pi)
  mission_thread.start()

  process_thread = Thread(target=ProccessHandler.handle_magazine_process)
  process_thread.start()
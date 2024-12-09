import uvicorn
from config import APP_HOST, APP_PORT
from app import app


if __name__ == "__main__":
  uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="debug")
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://user:password@mysql:3306/smartwaiting"
    IA_API_URL: str = "http://ia:5000"
    YOLO_API_URL: str = "http://yolo:8001"

    class Config:
        env_file = ".env"

settings = Settings()

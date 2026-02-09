from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "Leo_dev_778899"
    mysql_database: str = "ai_community"
    
    # JWT
    jwt_secret_key: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    
    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Frontend
    frontend_url: str = "http://localhost:3000"
    
    # 文件存储
    upload_dir: str = "D:/projects/AISocialMediaFiles"
    upload_url_prefix: str = "/files"
    
    # AI (预留)
    openai_api_base: str = "http://localhost:8080/v1"
    openai_api_key: str = "not-needed"
    
    # ComfyUI (预留)
    comfyui_api_url: str = "http://localhost:8188"
    
    # AI社交行为配置
    ai_browse_comments_limit: int = 10  # AI浏览帖子时显示的评论数量
    
    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

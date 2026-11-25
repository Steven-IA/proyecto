import os

class Settings:
    app_env = os.getenv("APP_ENV", "production")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/sentinelai.db")
    api_key = os.getenv("API_KEY", "change-me-in-production")
    authorized_subnet = os.getenv("AUTHORIZED_SUBNET", "192.168.1.0/24")
    model_dir = os.getenv("MODEL_DIR", "/app/models")
    data_dir = os.getenv("DATA_DIR", "/app/data")
    report_dir = os.getenv("REPORT_DIR", "/app/reports")

settings = Settings()
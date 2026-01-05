import os

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    ENABLE_AI = os.getenv("ENABLE_AI", "true").lower() == "true"
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_CONTENT_LENGTH", "10485760"))

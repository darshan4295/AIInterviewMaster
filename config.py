import os

# Database configuration
DB_USER = os.environ.get("PGUSER")
DB_PASSWORD = os.environ.get("PGPASSWORD")
DB_HOST = os.environ.get("PGHOST")
DB_PORT = os.environ.get("PGPORT")
DB_NAME = os.environ.get("PGDATABASE")
DATABASE_URL = os.environ.get("DATABASE_URL")

# OpenAI configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Judge0 API (code execution platform)
JUDGE0_API_KEY = os.environ.get("JUDGE0_API_KEY")
JUDGE0_API_URL = os.environ.get("JUDGE0_API_URL", "https://api.judge0.com")

# General application settings
APP_ENV = os.environ.get("APP_ENV", "development")
DEBUG = APP_ENV == "development"
PORT = int(os.environ.get("PORT", 8000))

# JWT Settings
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRY = 86400  # 24 hours

# File storage settings
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'mp4', 'avi', 'mkv', 'webm'}
UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/uploads")

# GitHub & LinkedIn API integration
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
LINKEDIN_CLIENT_ID = os.environ.get("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET")

# Scoring weights
SCORING_CONFIG = {
    'profile_weight': 0.2,
    'video_interview_weight': 0.3,
    'coding_challenge_weight': 0.4,
    'managerial_round_weight': 0.1,
}

# Supported programming languages for coding challenges
SUPPORTED_LANGUAGES = {
    'python': 71,
    'javascript': 63,
    'java': 62,
    'c': 50,
    'cpp': 54,
    'csharp': 51,
    'go': 60,
    'ruby': 72,
    'rust': 73,
    'typescript': 74,
}

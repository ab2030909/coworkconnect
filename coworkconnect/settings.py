from pathlib import Path
import os
from urllib.parse import parse_qs, urlparse, unquote


BASE_DIR = Path(__file__).resolve().parent.parent


def load_env():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", os.getenv("JWT_SECRET", "coworkconnect-dev-key"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "api.middleware.EnsureSchemaMiddleware",
    "api.middleware.CorsMiddleware",
]

ROOT_URLCONF = "coworkconnect.urls"
WSGI_APPLICATION = "coworkconnect.wsgi.application"
ASGI_APPLICATION = "coworkconnect.asgi.application"

def truthy(value):
    return str(value).lower() in {"1", "true", "yes", "on", "required"}


def database_config_from_env():
    database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")
    config = {
        "name": os.getenv("DB_NAME", "coworkconnect"),
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "port": os.getenv("DB_PORT", "3306"),
        "ssl": truthy(os.getenv("DB_SSL", "false")),
    }

    if database_url:
        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        config.update(
            {
                "name": parsed.path.lstrip("/") or config["name"],
                "host": parsed.hostname or config["host"],
                "user": unquote(parsed.username or config["user"]),
                "password": unquote(parsed.password or config["password"]),
                "port": str(parsed.port or config["port"]),
                "ssl": config["ssl"] or "ssl" in query or truthy(query.get("ssl-mode", [""])[0]),
            }
        )

    return config


DB_CONFIG = database_config_from_env()
DB_NAME = DB_CONFIG["name"]
DB_HOST = DB_CONFIG["host"]
DB_USER = DB_CONFIG["user"]
DB_PASSWORD = DB_CONFIG["password"]
DB_PORT = DB_CONFIG["port"]
DB_SSL = DB_CONFIG["ssl"]

try:
    import pymysql

    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=int(DB_PORT),
        charset="utf8mb4",
        autocommit=True,
        ssl={} if DB_SSL else None,
    )
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    connection.close()
except Exception:
    pass

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "OPTIONS": {
            "charset": "utf8mb4",
            **({"ssl": {}} if DB_SSL else {}),
        },
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = False

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "ui"]
MEDIA_URL = "/uploads/"
MEDIA_ROOT = BASE_DIR / "uploads"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
JWT_EXPIRE = os.getenv("JWT_EXPIRE", "30d")

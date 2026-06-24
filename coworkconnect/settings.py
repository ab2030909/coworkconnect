from pathlib import Path
import os
import tempfile
from urllib.parse import parse_qs, urlparse, unquote


BASE_DIR = Path(__file__).resolve().parent.parent


def load_env():
    if truthy(os.getenv("VERCEL", "false")):
        return

    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def truthy(value):
    return str(value).lower() in {"1", "true", "yes", "on", "require", "required"}


load_env()

DEBUG = truthy(os.getenv("DEBUG", "true"))
DEV_SECRET_KEY = "coworkconnect-local-development-secret-key-32"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY") or os.getenv("JWT_SECRET") or DEV_SECRET_KEY
JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)

if not DEBUG and (SECRET_KEY == DEV_SECRET_KEY or JWT_SECRET == DEV_SECRET_KEY):
    raise RuntimeError("Set DJANGO_SECRET_KEY and JWT_SECRET before running with DEBUG=false")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app").split(",")
    if host.strip()
]
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

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


def database_config_from_env():
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_PRISMA_URL")
        or os.getenv("POSTGRES_URL_NON_POOLING")
        or os.getenv("SUPABASE_DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
        or os.getenv("MYSQL_URL")
    )
    explicit_engine = os.getenv("DB_ENGINE")
    postgres_host = os.getenv("POSTGRES_HOST") or os.getenv("SUPABASE_DB_HOST")
    postgres_user = os.getenv("POSTGRES_USER") or os.getenv("SUPABASE_DB_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD") or os.getenv("SUPABASE_DB_PASSWORD")
    postgres_name = os.getenv("POSTGRES_DATABASE") or os.getenv("POSTGRES_DB") or os.getenv("SUPABASE_DB_NAME")
    postgres_port = os.getenv("POSTGRES_PORT") or os.getenv("SUPABASE_DB_PORT")

    inferred_engine = "postgresql" if any([postgres_host, postgres_user, postgres_password, postgres_name]) else "mysql"
    config = {
        "engine": explicit_engine or inferred_engine,
        "name": postgres_name or os.getenv("DB_NAME", "coworkconnect"),
        "host": postgres_host or os.getenv("DB_HOST", "localhost"),
        "user": postgres_user or os.getenv("DB_USER", "root"),
        "password": postgres_password or os.getenv("DB_PASSWORD", ""),
        "port": postgres_port or os.getenv("DB_PORT", "5432" if inferred_engine == "postgresql" else "3306"),
        "ssl": truthy(os.getenv("DB_SSL", "true" if inferred_engine == "postgresql" else "false")),
    }

    if database_url:
        parsed = urlparse(database_url)
        query = parse_qs(parsed.query)
        scheme = parsed.scheme.replace("+psycopg", "")
        engine = "postgresql" if scheme in {"postgres", "postgresql"} else "mysql"
        config.update(
            {
                "engine": engine,
                "name": parsed.path.lstrip("/") or config["name"],
                "host": parsed.hostname or config["host"],
                "user": unquote(parsed.username or config["user"]),
                "password": unquote(parsed.password or config["password"]),
                "port": str(parsed.port or ("5432" if engine == "postgresql" else config["port"])),
                "ssl": config["ssl"]
                or "ssl" in query
                or truthy(query.get("ssl-mode", [""])[0])
                or truthy(query.get("sslmode", [""])[0]),
            }
        )

    return config


HAS_EXTERNAL_DB_CONFIG = any(
    os.getenv(name)
    for name in [
        "DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRES_PRISMA_URL",
        "POSTGRES_URL_NON_POOLING",
        "SUPABASE_DATABASE_URL",
        "SUPABASE_DB_URL",
        "MYSQL_URL",
        "DB_HOST",
        "POSTGRES_HOST",
        "SUPABASE_DB_HOST",
    ]
)

USE_SQLITE_FALLBACK = (
    truthy(os.getenv("VERCEL", "false"))
    and not HAS_EXTERNAL_DB_CONFIG
)

DB_CONFIG = database_config_from_env()
DB_ENGINE = DB_CONFIG["engine"]
DB_NAME = DB_CONFIG["name"]
DB_HOST = DB_CONFIG["host"]
DB_USER = DB_CONFIG["user"]
DB_PASSWORD = DB_CONFIG["password"]
DB_PORT = DB_CONFIG["port"]
DB_SSL = DB_CONFIG["ssl"]

if not USE_SQLITE_FALLBACK and DB_ENGINE == "mysql":
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

if USE_SQLITE_FALLBACK:
    SQLITE_PATH = Path(os.getenv("SQLITE_PATH", Path(tempfile.gettempdir()) / "coworkconnect.sqlite3"))
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(SQLITE_PATH),
        }
    }
else:
    django_engine = "django.db.backends.postgresql" if DB_ENGINE == "postgresql" else "django.db.backends.mysql"
    db_options = {}
    if DB_ENGINE == "mysql":
        db_options = {
            "charset": "utf8mb4",
            **({"ssl": {}} if DB_SSL else {}),
        }
    elif DB_ENGINE == "postgresql" and DB_SSL:
        db_options = {"sslmode": "require"}

    DATABASES = {
        "default": {
            "ENGINE": django_engine,
            "NAME": DB_NAME,
            "USER": DB_USER,
            "PASSWORD": DB_PASSWORD,
            "HOST": DB_HOST,
            "PORT": DB_PORT,
            "OPTIONS": db_options,
        }
    }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Karachi"
USE_I18N = True
USE_TZ = False

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "ui"]
MEDIA_URL = "/uploads/"
MEDIA_ROOT = Path(tempfile.gettempdir()) / "uploads" if truthy(os.getenv("VERCEL", "false")) else BASE_DIR / "uploads"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

JWT_EXPIRE = os.getenv("JWT_EXPIRE", "30d")
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(5 * 1024 * 1024)))
ALLOWED_UPLOAD_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

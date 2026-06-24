from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from uuid import uuid4

import bcrypt
import jwt
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.http import JsonResponse


def api_response(payload, status=200):
    return JsonResponse(payload, status=status, encoder=DjangoJSONEncoder, safe=isinstance(payload, dict))


def read_data(request):
    content_type = request.META.get("CONTENT_TYPE", "")
    if "application/json" in content_type and request.body:
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


def fetch_all(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql" and sql.lstrip().lower().startswith("insert") and " returning " not in sql.lower():
            cursor.execute(f"{sql.rstrip()} RETURNING id", params or [])
            row = cursor.fetchone()
            return cursor.rowcount, row[0] if row else None

        cursor.execute(sql, params or [])
        return cursor.rowcount, cursor.lastrowid


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, stored_hash):
    if not password or not stored_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))


def _expiry_delta():
    value = str(settings.JWT_EXPIRE).strip().lower()
    try:
        if value.endswith("d"):
            return timedelta(days=int(value[:-1]))
        if value.endswith("h"):
            return timedelta(hours=int(value[:-1]))
        if value.endswith("m"):
            return timedelta(minutes=int(value[:-1]))
        return timedelta(seconds=int(value))
    except ValueError:
        return timedelta(days=30)


def make_token(user):
    payload = {
        "id": user["id"],
        "role": user.get("role", "user"),
        "exp": datetime.utcnow() + _expiry_delta(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def auth_user(request, required=True):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    token = None
    if header.startswith("Bearer "):
        token = header.split(" ", 1)[1]

    if not token:
        if required:
            return None, api_response({"success": False, "message": "Not authorized to access this route"}, 401)
        return None, None

    try:
        token_user = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user = fetch_one(
            "SELECT id, name, email, role FROM users WHERE id = %s",
            [token_user.get("id")],
        )
        if not user:
            raise jwt.InvalidTokenError("User no longer exists")
        return user, None
    except jwt.PyJWTError:
        if required:
            return None, api_response({"success": False, "message": "Not authorized to access this route"}, 401)
        return None, None


def require_admin(user):
    if user.get("role") != "admin":
        return api_response(
            {
                "success": False,
                "message": f"User role {user.get('role')} is not authorized to access this route",
            },
            403,
        )
    return None


def save_upload(file_obj, folder=""):
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 5 * 1024 * 1024)
    allowed_types = getattr(settings, "ALLOWED_UPLOAD_TYPES", {"image/jpeg", "image/png", "image/webp", "image/gif"})
    content_type = getattr(file_obj, "content_type", "")
    if content_type not in allowed_types:
        raise ValueError("Only JPG, PNG, WebP, and GIF images are supported")
    if getattr(file_obj, "size", 0) > max_size:
        raise ValueError("Image must be 5MB or smaller")

    upload_dir = Path(settings.MEDIA_ROOT) / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file_obj.name).suffix.lower()
    prefix = f"{folder.rstrip('/')}-" if folder else ""
    filename = f"{prefix}{int(time.time() * 1000)}-{uuid4().hex}{suffix}"
    destination = upload_dir / filename

    with destination.open("wb+") as target:
        for chunk in file_obj.chunks():
            target.write(chunk)

    if folder:
        return f"/uploads/{folder}/{filename}"
    return f"/uploads/{filename}"


def method_not_allowed():
    return api_response({"success": False, "message": "Method not allowed"}, 405)

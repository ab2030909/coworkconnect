from datetime import datetime, timedelta
from pathlib import Path
import json
import time
import os
from uuid import uuid4

import cloudinary
import cloudinary.uploader

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
    if request.method in ["PUT", "PATCH"] and "multipart/form-data" in content_type:
        from django.http.multipartparser import MultiPartParser
        try:
            post, files = MultiPartParser(request.META, request, request.upload_handlers).parse()
            request.POST = post
            request.FILES = files
            return post.dict()
        except Exception:
            return {}
    return request.POST.dict()


def fetch_all(sql, params=None):
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception:
        try:
            connection._rollback()
        except Exception:
            pass
        raise


def fetch_one(sql, params=None):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    try:
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql" and sql.lstrip().lower().startswith("insert") and " returning " not in sql.lower():
                cursor.execute(f"{sql.rstrip()} RETURNING id", params or [])
                row = cursor.fetchone()
                return cursor.rowcount, row[0] if row else None

            cursor.execute(sql, params or [])
            lastrowid = getattr(cursor, "lastrowid", None)
            if lastrowid is None and hasattr(cursor, "cursor"):
                lastrowid = getattr(cursor.cursor, "lastrowid", None)
            return cursor.rowcount, lastrowid
    except Exception:
        try:
            connection._rollback()
        except Exception:
            pass
        raise


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
            if required:
                return None, api_response({"success": False, "message": "User not found"}, 401)
            return None, None
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
    max_size = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)
    allowed_types = getattr(settings, "ALLOWED_UPLOAD_TYPES", {
        "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif",
        "image/avif", "image/heic", "image/heif", "image/svg+xml", "image/bmp",
        "image/tiff", "image/jfif", "image/x-icon", "image/pjpeg"
    })
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".heic", ".heif", ".svg", ".bmp", ".tiff", ".jfif"}
    content_type = getattr(file_obj, "content_type", "").lower()
    suffix = Path(file_obj.name).suffix.lower() if getattr(file_obj, "name", None) else ""

    if content_type not in allowed_types and suffix not in allowed_extensions:
        raise ValueError("Unsupported image format. Please upload JPG, PNG, WebP, GIF, AVIF, HEIC, SVG, or BMP.")
    if getattr(file_obj, "size", 0) > max_size:
        raise ValueError("Image must be 10MB or smaller")

    cloudinary_url = os.environ.get("CLOUDINARY_URL")
    if cloudinary_url:
        # Use Cloudinary if the env var is set
        try:
            res = cloudinary.uploader.upload(file_obj, folder=folder)
            return res.get("secure_url")
        except Exception as e:
            raise ValueError(f"Cloudinary upload failed: {e}")

    # Fallback to local storage with PIL image compression
    upload_dir = Path(settings.MEDIA_ROOT) / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file_obj.name).suffix.lower() if getattr(file_obj, "name", None) else ".jpg"
    prefix = f"{folder.rstrip('/')}-" if folder else ""
    filename = f"{prefix}{int(time.time() * 1000)}-{uuid4().hex}{suffix}"
    destination = upload_dir / filename

    try:
        from PIL import Image, ImageOps

        if suffix in [".svg", ".gif"]:
            # Write SVGs and animated GIFs directly without altering frames
            with destination.open("wb+") as target:
                for chunk in file_obj.chunks():
                    target.write(chunk)
        else:
            # Compress raster image using PIL
            file_obj.seek(0)
            img = Image.open(file_obj)

            # Auto-orient EXIF camera photos
            img = ImageOps.exif_transpose(img)

            # Resize if dimensions exceed 1920x1920
            max_dim = 1920
            width, height = img.size
            if width > max_dim or height > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            # Mode handling
            if img.mode in ("RGBA", "LA", "P") and suffix not in [".png", ".webp"]:
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                img = bg
            elif img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")

            # Compress and save
            if suffix == ".webp":
                img.save(destination, "WEBP", quality=82)
            elif suffix in [".jpg", ".jpeg", ".jfif", ".pjpeg"]:
                img.save(destination, "JPEG", quality=82, optimize=True)
            elif suffix == ".png":
                img.save(destination, "PNG", optimize=True)
            else:
                destination = destination.with_suffix(".jpg")
                filename = destination.name
                img.save(destination, "JPEG", quality=82, optimize=True)

    except Exception as e:
        # Direct stream fallback on error
        file_obj.seek(0)
        with destination.open("wb+") as target:
            for chunk in file_obj.chunks():
                target.write(chunk)

    if folder:
        return f"/uploads/{folder}/{filename}"
    return f"/uploads/{filename}"


def method_not_allowed():
    return api_response({"success": False, "message": "Method not allowed"}, 405)

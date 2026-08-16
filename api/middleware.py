class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            from django.http import HttpResponse

            response = HttpResponse()
        else:
            response = self.get_response(request)

        from django.conf import settings

        origin = request.META.get("HTTP_ORIGIN", "")
        allowed = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
        if allowed and origin in allowed:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
        elif not allowed and settings.DEBUG:
            response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return response


_schema_done = False


class EnsureSchemaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _schema_done
        if not _schema_done:
            from .schema import ensure_schema

            try:
                ensure_schema()
            except Exception:
                pass
            _schema_done = True
        return self.get_response(request)


import time
from django.http import JsonResponse

_rate_limit_store = {}
MAX_AUTH_ATTEMPTS = 5
AUTH_WINDOW_SECONDS = 60


class AuthRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.rstrip("/").lower()
        if request.method == "POST" and path in ("/api/auth/login", "/api/auth/register"):
            ip = self.get_client_ip(request)
            now = time.time()

            attempts = [t for t in _rate_limit_store.get(ip, []) if now - t < AUTH_WINDOW_SECONDS]
            if len(attempts) >= MAX_AUTH_ATTEMPTS:
                retry_after = int(AUTH_WINDOW_SECONDS - (now - attempts[0]))
                response = JsonResponse({
                    "success": False,
                    "message": f"Too many authentication attempts. Please wait {max(1, retry_after)} seconds before trying again."
                }, status=429)
                response["Retry-After"] = str(max(1, retry_after))
                return response

            attempts.append(now)
            _rate_limit_store[ip] = attempts

        return self.get_response(request)

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")


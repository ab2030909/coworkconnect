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


class EnsureSchemaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from .schema import ensure_schema

        ensure_schema()
        return self.get_response(request)

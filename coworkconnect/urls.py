from django.conf import settings
from django.http import Http404, HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


def home(_request):
    return HttpResponse("CoWorkConnect API is running")


def serve_ui(request, path="index.html"):
    target = path or "index.html"
    
    # Serve the newly created login.html file natively
    if target in ["login", "signin", "signin.html"]:
        target = "login.html"
        
    # Handle extensionless HTML routes
    if not target.endswith((".html", ".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".json")):
        html_target = f"{target}.html"
        if (settings.BASE_DIR / "ui" / html_target).exists():
            target = html_target

    try:
        response = serve(request, target, document_root=settings.BASE_DIR / "ui")
        if str(target).endswith((".html", ".js", ".css")):
            response["Cache-Control"] = "no-store, max-age=0"
        return response
    except Http404:
        # SPA Fallback: If not found, serve index.html instead of erroring out
        return serve(request, "index.html", document_root=settings.BASE_DIR / "ui")


urlpatterns = [
    path("api/", include("api.urls")),
    path("uploads/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    path("", serve_ui),
    re_path(r"^(?P<path>.*)$", serve_ui),
]

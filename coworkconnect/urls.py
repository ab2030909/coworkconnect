from django.conf import settings
from django.http import Http404, HttpResponse
from django.urls import include, path, re_path
from django.views.static import serve


def home(_request):
    return HttpResponse("CoWorkConnect API is running")


def serve_ui(request, path="index.html"):
    target = path or "index.html"
    if target == "login.html":
        target = "index.html"
    try:
        response = serve(request, target, document_root=settings.BASE_DIR / "ui")
        if str(target).endswith((".html", ".js", ".css")):
            response["Cache-Control"] = "no-store, max-age=0"
        return response
    except Http404:
        raise


urlpatterns = [
    path("api/", include("api.urls")),
    path("uploads/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    path("", serve_ui),
    re_path(r"^(?P<path>.*)$", serve_ui),
]

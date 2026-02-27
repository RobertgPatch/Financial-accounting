from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path('healthz', health_check, name='health-check'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]

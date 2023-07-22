from django.urls import path
from . import device_views

urlpatterns = [
    path("logged_in_devices/", device_views.DeviceDataAPI.as_view()),
    path("log_out_device/<str:device_id>", device_views.DeviceDataAPI.as_view())
]

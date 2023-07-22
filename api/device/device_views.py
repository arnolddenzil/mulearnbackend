from rest_framework.views import APIView

from db.device import Device
from utils.permission import CustomizePermission, JWTUtils, DateTimeUtils, role_required
from utils.response import CustomResponse
from django.core.cache import cache
from .serializer import DeviceSerializer


class DeviceDataAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request):
        device_id = JWTUtils.fetch_device_id(request)
        user_id = JWTUtils.fetch_user_id(request)
        devices_except_for_caller_device = Device.objects.filter(user=user_id).exclude(id=device_id).all()
        device_serializer = DeviceSerializer(devices_except_for_caller_device, many=True)
        return CustomResponse(response={'devices': device_serializer.data}).get_success_response()

    def delete(self, request, device_id):
        device = Device.objects.filter(id=device_id).first()

        if not device:
            return CustomResponse(general_message="Device not found").get_failure_response()

        cache.delete(f"Device:{device_id}")
        device.delete()
        return CustomResponse(general_message="Device logged out successfully").get_success_response()
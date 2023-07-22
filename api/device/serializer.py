from rest_framework import serializers
from db.device import Device
from django.core.cache import cache


class DeviceSerializer(serializers.ModelSerializer):
    last_active_at = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = ["id", "last_active_at", "browser", "os", "last_log_in"]

    def get_last_active_at(self, obj):
        last_active_at = cache.get(f"Device:{obj.id}")
        return last_active_at


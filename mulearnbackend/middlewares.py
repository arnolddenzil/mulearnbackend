import hmac
import logging

import decouple
from django.http import JsonResponse
from rest_framework import status

from utils.utils import _CustomHTTPHandler, DateTimeUtils
from utils.response import CustomResponse
from utils.permission import JWTUtils
from django.core.cache import cache
import time

logger = logging.getLogger(__name__)


class IpBindingMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.META.get("PATH_INFO").split("/")[-1]
        if path == "discord-id":
            client_ip = _CustomHTTPHandler().get_client_ip_address(request)
            arron_ip = decouple.config("AARON_CHETTAN_IP")

            if client_ip != arron_ip:
                return JsonResponse(
                    {
                        "hasError": True,
                        "statusCode": status.HTTP_401_UNAUTHORIZED,
                        "message": "Ip not verified",
                        "response": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        response = self.get_response(request)
        return response


class ApiSignatureMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        api_path = "/".join(request.META.get("PATH_INFO").split("/")[-3:-1])
        if api_path == "lc/user-validation":
            signature = request.META.get("HTTP_SIGNATURE")
            timestamp = request.META.get("HTTP_TIMESTAMP")
            host = request.META.get("HTTP_HOST")
            request_path = request.META.get("PATH_INFO")
            request_method = request.META.get("REQUEST_METHOD")
            key = f"{request_path}::{request_method}::{timestamp}"
            new_signature = hmac.new(
                key=decouple.config("SECRET_KEY").encode(), msg=key.encode(), digestmod="SHA256"
            ).hexdigest()
            print(new_signature)
            if new_signature != signature:
                return JsonResponse(
                    {
                        "hasError": True,
                        "statusCode": status.HTTP_401_UNAUTHORIZED,
                        "message": "Signature not verified",
                        "response": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        response = self.get_response(request)
        return response


class DeviceCheck(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/api/v1/register/":
            return self.get_response(request)

        device_id = JWTUtils.fetch_device_id(request)

        # Performance check
        redis_start_time = time.time()
        device = cache.get(f"Device:{device_id}")
        redis_end_time = time.time()
        elapsed_redis_time = redis_end_time - redis_start_time
        print(f"Redis Elapsed Time: {elapsed_redis_time} sec")

        if device:
            cache.set(key=f"Device:{device_id}", value=str(DateTimeUtils.get_current_utc_time()), timeout=None)
            return self.get_response(request)
        else:
            return CustomResponse(general_message="Device logged out").get_failure_response()

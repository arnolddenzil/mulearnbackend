import decouple
import requests
from django.core.mail import send_mail
from django.db.models import Q
from rest_framework.views import APIView

from db.organization import Country, District, Organization, Department, State, Zone
from db.task import InterestGroup
from db.user import Role, User
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType,TasksTypesHashtag
from . import serializers


class LearningCircleUserViewAPI(APIView):
    def post(self, request):
        mu_id = request.headers.get("muid")
        user = User.objects.filter(mu_id=mu_id).first()
        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()
        serializer = serializers.LearningCircleUserSerializer(user)
        id, mu_id, first_name, last_name, email, phone = serializer.data.values()
        name = f"{first_name}{last_name or ''}"
        return CustomResponse(
            response={
                "id": id,
                "mu_id": mu_id,
                "name": name,
                "email": email,
                "phone": phone,
            }
        ).get_success_response()


class RegisterDataAPI(APIView):
    def post(self, request):
        data = request.data
        create_user = serializers.RegisterSerializer(
            data=data, context={"request": request}
        )

        if not create_user.is_valid():
            return CustomResponse(
                message=create_user.errors, general_message="Invalid fields"
            ).get_failure_response()
        user_obj, password = create_user.save()

        auth_domain = decouple.config("AUTH_DOMAIN")

        response = requests.post(
            f"{auth_domain}/api/v1/auth/user-authentication/",
            data={"emailOrMuid": user_obj.mu_id, "password": password,
                  "httpUserAgent": request.data.get("httpUserAgent")},
        )
        response = response.json()
        if response.get("statusCode") != 200:
            return CustomResponse(
                message=response.get("message")
            ).get_failure_response()
        res_data = response.get("response")
        access_token = res_data.get("accessToken")
        refresh_token = res_data.get("refreshToken")

        # send_mail("Congrats, You have been successfully registered in μlearn", f" Your Muid {user_obj.mu_id}",
        #           decouple.config("EMAIL_HOST_USER"), [user_obj.email], fail_silently=False)

        return CustomResponse(
            response={
                "data": serializers.UserDetailSerializer(
                    user_obj, many=False
                ).data,
                "accessToken": access_token,
                "refreshToken": refresh_token,
            }
        ).get_success_response()


class RoleAPI(APIView):
    def get(self, request):
        roles = [RoleType.STUDENT.value, RoleType.MENTOR.value, RoleType.ENABLER.value]
        role_serializer = Role.objects.filter(title__in=roles)
        role_serializer_data = serializers.OrgSerializer(
            role_serializer, many=True
        ).data
        return CustomResponse(
            response={"roles": role_serializer_data}
        ).get_success_response()


class DepartmentAPI(APIView):
    def get(self, request):
        department_serializer = Department.objects.all()
        department_serializer_data = serializers.DepartmentSerializer(
            department_serializer, many=True
        ).data
        return CustomResponse(
            response={"department": department_serializer_data}
        ).get_success_response()


class CountryAPI(APIView):
    def get(self, request):
        countries = Country.objects.all()
        serializer = serializers.CountrySerializer(countries, many=True)
        return CustomResponse(
            response={
                "countries": serializer.data,
            }
        ).get_success_response()


class StateAPI(APIView):
    def post(self, request):
        print(request.data.get("country"))
        state = State.objects.filter(country_id=request.data.get("country"))
        serializer = serializers.StateSerializer(state, many=True)
        return CustomResponse(
            response={
                "states": serializer.data,
            }
        ).get_success_response()


class DistrictAPI(APIView):
    def post(self, request):
        district = District.objects.filter(zone__state_id=request.data.get("state"))
        serializer = serializers.DistrictSerializer(district, many=True)
        return CustomResponse(
            response={
                "districts": serializer.data,
            }
        ).get_success_response()


class CollegeAPI(APIView):
    def post(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.COLLEGE.value),
            Q(district_id=request.data.get("district")),
        )
        department_queryset = Department.objects.all()
        college_serializer_data = serializers.OrgSerializer(
            org_queryset, many=True
        ).data
        department_serializer_data = serializers.OrgSerializer(
            department_queryset, many=True
        ).data
        return CustomResponse(
            response={
                "colleges": college_serializer_data,
                "departments": department_serializer_data,
            }
        ).get_success_response()


class CompanyAPI(APIView):
    def get(self, request):
        company_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMPANY.value
        )
        company_serializer_data = serializers.OrgSerializer(
            company_queryset, many=True
        ).data
        return CustomResponse(
            response={"companies": company_serializer_data}
        ).get_success_response()


class CommunityAPI(APIView):
    def get(self, request):
        community_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMMUNITY.value
        )
        community_serializer_data = serializers.OrgSerializer(
            community_queryset, many=True
        ).data
        return CustomResponse(
            response={"communities": community_serializer_data}
        ).get_success_response()


class AreaOfInterestAPI(APIView):
    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()
        aoi_serializer_data = serializers.AreaOfInterestAPISerializer(
            aoi_queryset, many=True
        ).data
        return CustomResponse(
            response={"aois": aoi_serializer_data}
        ).get_success_response()


class UserEmailVerificationAPI(APIView):
    def post(self, request):
        user_email = request.data.get("email")
        if user := User.objects.filter(email=user_email).first():
            return CustomResponse(
                general_message="This email already exists", response={"value": True}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="User email not exist", response={"value": False}
            ).get_success_response()


class UserCountryAPI(APIView):
    def get(self, request):
        country = Country.objects.all()
        if country is None:
            return CustomResponse(
                general_message="No data available"
            ).get_success_response()
        country_serializer = serializers.UserCountrySerializer(country, many=True).data
        return CustomResponse(response=country_serializer).get_success_response()


class UserStateAPI(APIView):
    def get(self, request):
        country_name = request.data.get("country")

        country_object = Country.objects.filter(name=country_name).first()
        if country_object is None:
            return CustomResponse(
                general_message="No country data available"
            ).get_success_response()

        state_object = State.objects.filter(country_id=country_object).all()
        if len(state_object) == 0:
            return CustomResponse(
                general_message="No state data available for given country"
            ).get_success_response()

        state_serializer = serializers.UserStateSerializer(state_object, many=True).data
        return CustomResponse(response=state_serializer).get_success_response()


class UserZoneAPI(APIView):
    def get(self, request):
        state_name = request.data.get("state")

        state_object = State.objects.filter(name=state_name).first()
        if state_object is None:
            return CustomResponse(
                general_message="No state data available"
            ).get_success_response()

        zone_object = Zone.objects.filter(state_id=state_object).all()
        if len(zone_object) == 0:
            return CustomResponse(
                general_message="No zone data available for given country"
            ).get_success_response()

        zone_serializer = serializers.UserZoneSerializer(zone_object, many=True).data
        return CustomResponse(response=zone_serializer).get_success_response()

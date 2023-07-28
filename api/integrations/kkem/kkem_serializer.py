from django.db.utils import IntegrityError
from rest_framework import serializers
from django.db.models import Sum
from db.integrations import IntegrationAuthorization, Integration
from db.task import KarmaActivityLog, UserIgLink

from db.user import User
from utils.utils import DateTimeUtils
from django.db.models import Q


class KKEMUserSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    dwms_id = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        karma = (
            obj.total_karma_user.karma
            if hasattr(obj, "total_karma_user")
            and hasattr(obj.total_karma_user, "karma")
            else 0
        )
        return karma

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = (
                0
                if KarmaActivityLog.objects.filter(task__ig=ig_link.ig, user=obj)
                .aggregate(Sum("karma"))
                .get("karma__sum")
                is None
                else KarmaActivityLog.objects.filter(task__ig=ig_link.ig, user=obj)
                .aggregate(Sum("karma"))
                .get("karma__sum")
            )
            interest_groups.append({"name": ig_link.ig.name, "karma": total_ig_karma})
        return interest_groups

    def get_dwms_id(self, obj):
        return (
            IntegrationAuthorization.objects.filter(user=obj, verified=True)
            .first()
            .integration_value
        )

    class Meta:
        model = User
        fields = [
            "mu_id",
            "dwms_id",
            "total_karma",
            "interest_groups",
        ]


class KKEMAuthorization(serializers.ModelSerializer):
    emailOrMuid = serializers.CharField(source="user.mu_id")
    dwms_id = serializers.CharField(source="integration_value")
    integration = serializers.CharField(source="integration.name")

    def create(self, validated_data):
        user_mu_id = validated_data["user"]["mu_id"]

        try:
            if not (
                user := User.objects.filter(
                    Q(mu_id=user_mu_id) | Q(email=user_mu_id)
                ).first()
            ):
                raise ValueError("User doesn't exist")
            integration = Integration.objects.get(
                name=validated_data["integration"]["name"]
            )
        except Integration.DoesNotExist as e:
            raise ValueError("Invalid request token") from e

        try:
            kkem_link = IntegrationAuthorization.objects.create(
                integration=integration,
                user=user,
                verified=validated_data["verified"],
                integration_value=validated_data["integration_value"],
                created_at=DateTimeUtils.get_current_utc_time(),
                updated_at=DateTimeUtils.get_current_utc_time(),
            )

        except IntegrityError as e:
            kkem_link = IntegrationAuthorization.objects.filter(user=user).first()
            if (
                not kkem_link
                and IntegrationAuthorization.objects.filter(
                    integration_value=validated_data["integration_value"]
                ).first()
            ):
                raise ValueError(
                    "This dwms_id is already associated with another user"
                ) from e
            elif (
                self.context["type"] == "login"
                and kkem_link.integration_value == validated_data["integration_value"]
                and kkem_link.verified == True
            ):
                return kkem_link
            elif kkem_link.verified:
                raise ValueError("Authorization already exists and is verified.") from e
            elif kkem_link.user == user:
                kkem_link.integration_value = validated_data["integration_value"]
                kkem_link.updated_at = DateTimeUtils.get_current_utc_time()
                kkem_link.verified = validated_data["verified"]
                kkem_link.save()
            else:
                raise

        return {
            "email": kkem_link.user.email,
            "fullname": kkem_link.user.fullname,
            "mu_id": kkem_link.user.mu_id,
            "dwms_id": kkem_link.integration_value,
            "link_id": kkem_link.id,
        }

    class Meta:
        model = IntegrationAuthorization
        fields = ["emailOrMuid", "dwms_id", "integration", "verified"]

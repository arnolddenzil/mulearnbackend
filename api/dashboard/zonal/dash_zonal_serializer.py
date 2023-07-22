from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink
from db.task import KarmaActivityLog, Level,UserLvlLink
from db.user import User
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class ZonalStudents(serializers.ModelSerializer):
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()

    def get_rank(self, obj):
        queryset = self.context["queryset"]
        sorted_persons = sorted(
            queryset,
            key=lambda x: x.karma,
            reverse=True,
        )
        for i, person in enumerate(sorted_persons):
            if person == obj:
                return i + 1

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "mobile",
            "mu_id",
            "karma",
            "rank",
        ]


class ZonalCampus(serializers.ModelSerializer):
    total_karma = serializers.IntegerField()
    total_members = serializers.IntegerField()
    active_members = serializers.IntegerField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "title",
            "code",
            "org_type",
            "total_karma",
            "total_members",
            "active_members",
            "rank"
        ]

    def get_rank(self, obj):
        queryset = self.context["queryset"]

        sorted_campuses = sorted(
            queryset,
            key=lambda campus: campus.total_karma,
            reverse=True,
        )
        for i, campus in enumerate(sorted_campuses):
            if campus == obj:
                return i + 1


class ZonalDetailsSerializer(serializers.ModelSerializer):
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    zonal_lead = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = ["zone", "rank", "zonal_lead", "karma", "total_members", "active_members"]

    def get_rank(self, obj):

        user_org_link = UserOrganizationLink.objects.filter(org__org_type=OrganizationType.COLLEGE.value).values(
            'org', 'org__district__zone__name').annotate(total_karma=Sum('user__total_karma_user__karma'
                                                                         )).order_by('-total_karma')
        rank_dict = {}
        for data in user_org_link:
            zone_name = data['org__district__zone__name']
            total_karma = data['total_karma']

            if zone_name in rank_dict:
                rank_dict[zone_name] += total_karma
            else:
                rank_dict[zone_name] = total_karma

        sorted_rank_dict = dict(sorted(rank_dict.items(), key=lambda x: x[1], reverse=True))

        if obj.org.district.zone.name in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.district.zone.name)
            return position + 1

    def get_zonal_lead(self, obj):
        user_org_link = UserOrganizationLink.objects.\
            filter(org__district__zone__name=obj.org.district.zone.name,
                   user__user_role_link_user__role__title=RoleType.ZONAL_CAMPUS_LEAD.value).first()
        return user_org_link.user.fullname

    def get_karma(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(
            org__district__zone__name=obj.org.district.zone.name).aggregate(
            total_karma=Sum('user__total_karma_user__karma'))['total_karma']
        return user_org_link

    def get_total_members(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(org__district__zone__name=obj.org.district.zone.name).all()
        return len(user_org_link)

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=start_date.month % 12 + 1) - timedelta(days=1)
        user_org_link = UserOrganizationLink.objects.filter(org__district__zone__name=obj.org.district.zone.name).all()
        active_members = []
        for data in user_org_link:
            karma_activity_log = KarmaActivityLog.objects.filter(created_by=data.user, created_at__range=(
                start_date, end_date)).first()
            if karma_activity_log is not None:
                active_members.append(karma_activity_log)
        return len(active_members)


class TopThreeDistrictSerializer(serializers.ModelSerializer):

    rank = serializers.SerializerMethodField()
    district = serializers.CharField(source='org.district.name')

    class Meta:
        model = UserOrganizationLink
        fields = ["rank", "district"]

    def get_rank(self, obj):

        rank = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district__zone__name=obj.org.district.zone.name, verified=True,
            user__total_karma_user__isnull=False).values('org__district').annotate(
            total_karma=Sum('user__total_karma_user__karma')).order_by('-total_karma')
        district_ranks = {district['org__district']: i + 1 for i, district in enumerate(rank)}
        district_id = obj.org.district.id
        return district_ranks.get(district_id)


class StudentLevelStatusSerializer(serializers.ModelSerializer):

    college = serializers.CharField(source='org.title')
    level = serializers.SerializerMethodField()
    class Meta:
        model = UserOrganizationLink
        fields = ["college", "level"]

    def get_level(self, obj):
        level = Level.objects.all()
        level_dict = {}
        level_list = []
        for levels in level:
            level_dict['level'] = levels.level_order
            level_dict['students_count'] = len(UserLvlLink.objects.filter(level=levels, user=obj.user).all())
            level_list.append(level_dict)
            level_dict = {}
        return level_list
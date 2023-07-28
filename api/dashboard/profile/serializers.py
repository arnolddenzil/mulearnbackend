from django.db.models import Sum, F, Q, Prefetch
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.task import KarmaActivityLog, TotalKarma, UserIgLink, Level, TaskList
from db.user import User, UserSettings
from utils.permission import JWTUtils
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class UserLogSerializer(ModelSerializer):
    task_name = serializers.ReadOnlyField(source='task.title')
    created_date = serializers.CharField(source='created_at')

    class Meta:
        model = KarmaActivityLog
        fields = ["task_name", "karma", "created_date"]


class UserProfileSerializer(serializers.ModelSerializer):
    joined = serializers.DateTimeField(source="created_at")
    muid = serializers.CharField(source="mu_id")
    roles = serializers.SerializerMethodField()
    college_code = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma_distribution = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    is_public = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'joined', 'first_name', 'last_name', 'gender', 'muid', 'roles', 'college_code', 'karma', 'rank',
            'karma_distribution', 'level', 'profile_pic', 'interest_groups', 'is_public'
        )

    def get_is_public(self, obj):
        is_public_status = UserSettings.objects.filter(
            user=obj).first().is_public
        return is_public_status

    def get_roles(self, obj):
        return list(obj.user_role_link_user.values_list('role__title', flat=True))

    def get_college_code(self, obj):
        user_org_link = obj.user_organization_link_user_id.filter(
            org__org_type=OrganizationType.COLLEGE.value).first()
        if user_org_link:
            return user_org_link.org.code
        return None

    def get_karma(self, obj):
        total_karma = obj.total_karma_user
        if total_karma:
            return total_karma.karma
        return None

    def get_rank(self, obj):
        roles = self.context.get('roles')
        user_karma = obj.total_karma_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.MENTOR.value,
                                              karma__gte=user_karma).count()
        elif RoleType.ENABLER.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.ENABLER.value,
                                              karma__gte=user_karma).count()
        else:
            ranks = TotalKarma.objects.filter(karma__gte=user_karma).exclude(
                Q(user__user_role_link_user__role__title__in=[RoleType.ENABLER.value, RoleType.MENTOR.value])).count()
        return ranks if ranks > 0 else None

    def get_karma_distribution(self, obj):
        karma_distribution = (
            KarmaActivityLog.objects
            .filter(user=obj)
            .values(task_type=F('task__type__title'))
            .annotate(karma=Sum('karma'))
            .order_by()
        )

        return karma_distribution

    def get_level(self, obj):
        user_level_link = obj.userlvllink_set.first()
        if user_level_link:
            return user_level_link.level.name
        return None

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            total_ig_karma = 0 if KarmaActivityLog.objects.filter(task__ig=ig_link.ig, user=obj).aggregate(
                Sum('karma')).get('karma__sum') is None else KarmaActivityLog.objects.filter(task__ig=ig_link.ig,
                                                                                             user=obj).aggregate(
                Sum('karma')).get('karma__sum')
            interest_groups.append({'name': ig_link.ig.name, 'karma': total_ig_karma})
        return interest_groups


class UserLevelSerializer(serializers.ModelSerializer):
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ('name', 'tasks', 'karma')

    def get_tasks(self, obj):
        user_id = self.context.get('user_id')
        tasks = TaskList.objects.filter(level=obj).prefetch_related(
            Prefetch('karmaactivitylog_set',
                     queryset=KarmaActivityLog.objects.filter(user=user_id, appraiser_approved=True))
        )

        data = []
        for task in tasks:
            completed = task.karmaactivitylog_set.exists()
            if task.active or completed:
                data.append({
                    'task_name': task.title,
                    'hashtag': task.hashtag,
                    'completed': completed,
                    'karma': task.karma,
                })
        return data


class UserRankSerializer(ModelSerializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'role',
                  'rank', 'karma', 'interest_groups')

    def get_role(self, obj):
        roles = self.context.get('roles')
        if len(roles) == 0:
            return ['Learner']
        return roles

    def get_rank(self, obj):
        roles = self.context.get('roles')
        user_karma = obj.total_karma_user.karma
        if RoleType.MENTOR.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.MENTOR.value,
                                              karma__gte=user_karma).count()
        elif RoleType.ENABLER.value in roles:
            ranks = TotalKarma.objects.filter(user__user_role_link_user__role__title=RoleType.ENABLER.value,
                                              karma__gte=user_karma).count()
        else:
            ranks = TotalKarma.objects.filter(karma__gte=user_karma).exclude(
                Q(user__user_role_link_user__role__title__in=[RoleType.ENABLER.value, RoleType.MENTOR.value])).count()
        return ranks if ranks > 0 else None

    def get_karma(self, obj):
        total_karma = obj.total_karma_user
        if total_karma:
            return total_karma.karma
        return None

    def get_interest_groups(self, obj):
        interest_groups = []
        for ig_link in UserIgLink.objects.filter(user=obj):
            interest_groups.append(ig_link.ig.name)
        return interest_groups


class ShareUserProfileUpdateSerializer(ModelSerializer):
    updated_by = serializers.CharField(required=False)
    updated_at = serializers.CharField(required=False)

    class Meta:
        model = UserSettings
        fields = ("is_public", "updated_by", "updated_at")

    def update(self, instance, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.is_public = validated_data.get(
            'is_public', instance.is_public)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

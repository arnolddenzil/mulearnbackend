import uuid

from django.db import models

from db.user import User


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=200, blank=False)
    button = models.CharField(max_length=10, blank=True, null=True)
    url = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="created_notifications",
    )

    class Meta:
        managed = False
        db_table = "notification"
        ordering = ["created_at"]
from django.db import models
from db.user import User


class Device(models.Model):
    id = models.CharField(primary_key=True, max_length=64)
    browser = models.CharField(max_length=45, null=False)
    os = models.CharField(max_length=45, null=False)
    user = models.ForeignKey(User, models.DO_NOTHING)
    last_log_in = models.DateTimeField(null=False)

    class Meta:
        managed = False
        db_table = 'device'

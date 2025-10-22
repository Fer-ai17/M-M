from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile
from django.contrib.auth.models import User

@receiver(post_save, sender=Profile)
def sync_role_to_user(sender, instance, **kwargs):
    user = instance.user
    if not user:
        return
    if instance.role and instance.role.name.lower() == "admin":
        if not user.is_staff:
            user.is_staff = True
            user.save()
    # optional: remove is_staff when role changed away from admin
    # else:
    #     if user.is_staff:
    #         user.is_staff = False
    #         user.save()
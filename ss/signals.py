from django.contrib.auth.models import Group, User
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import ContentConsumer


CONSUMER_GROUP_NAME = "Consumidor de contingut"


@receiver(m2m_changed, sender=User.groups.through)
def sync_content_consumer_profile(sender, instance, action, pk_set, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    try:
        consumer_group = Group.objects.get(name=CONSUMER_GROUP_NAME)
    except Group.DoesNotExist:
        return

    if action == "post_add" and pk_set and consumer_group.pk in pk_set:
        ContentConsumer.objects.get_or_create(user=instance)
        return

    has_consumer_role = instance.groups.filter(pk=consumer_group.pk).exists()
    if not has_consumer_role:
        ContentConsumer.objects.filter(user=instance).delete()

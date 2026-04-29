from django.contrib.auth.models import Group, User
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import ContentConsumer
from .roles import ROLE_CONTENT_CONSUMER, get_role_group

@receiver(m2m_changed, sender=User.groups.through)
def sync_content_consumer_profile(sender, instance, action, pk_set, **kwargs):
    if action not in {"post_add", "post_remove", "post_clear"}:
        return

    try:
        consumer_group = get_role_group(ROLE_CONTENT_CONSUMER)
    except KeyError:
        return
    except Group.DoesNotExist:
        return

    if action == "post_add" and pk_set and consumer_group.pk in pk_set:
        if not ContentConsumer.objects.filter(pk=instance.pk).exists():
            ContentConsumer.objects.create(user_ptr_id=instance.pk)
        return

    has_consumer_role = instance.groups.filter(pk=consumer_group.pk).exists()
    if not has_consumer_role:
        ContentConsumer.objects.filter(pk=instance.pk).delete()

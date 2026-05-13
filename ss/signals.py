from django.contrib.auth.models import Group, User
from django.db import IntegrityError, connection
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import ContentConsumer
from .roles import ROLE_CONTENT_CONSUMER, get_role_group


def create_content_consumer_profile(user_id):
    table = connection.ops.quote_name(ContentConsumer._meta.db_table)
    pk_column = connection.ops.quote_name(ContentConsumer._meta.pk.column)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} ({pk_column}) VALUES (%s)",
                [user_id],
            )
    except IntegrityError:
        pass


def delete_content_consumer_profile(user_id):
    through = ContentConsumer.preferred_genres.through
    through.objects.filter(contentconsumer_id=user_id).delete()

    table = connection.ops.quote_name(ContentConsumer._meta.db_table)
    pk_column = connection.ops.quote_name(ContentConsumer._meta.pk.column)
    with connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {table} WHERE {pk_column} = %s",
            [user_id],
        )


@receiver(m2m_changed, sender=User.groups.through)
def sync_user_role_profiles(sender, instance, action, pk_set, **kwargs):
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
            create_content_consumer_profile(instance.pk)

    has_consumer_role = instance.groups.filter(pk=consumer_group.pk).exists()
    if not has_consumer_role:
        delete_content_consumer_profile(instance.pk)

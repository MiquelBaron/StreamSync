"""
Pasos reutilizables para preparar la base de datos de desarrollo.
Los comandos create_roles, create_admin_user y populate_demo_data delegan aquí.
"""
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from ss.models import (
    AgeRating,
    Country,
    Director,
    Film,
    Genre,
    Language,
    Platform,
    Serie,
)
from ss.roles import ROLE_CONTENT_CONSUMER, ROLE_DEFINITIONS, ensure_role_groups, get_role_group


def run_create_roles(stdout_write, style):
    for role_key, role_name in ROLE_DEFINITIONS.items():
        _, created = Group.objects.get_or_create(name=role_name)
        if created:
            stdout_write(style.SUCCESS(f"Group '{role_name}' created correctly (id='{role_key}')."))
        else:
            stdout_write(style.WARNING(f"Group '{role_name}' already exists (id='{role_key}')."))


def run_create_admin_user(stdout_write, style):
    User = get_user_model()
    username = "admin"
    password = "admin"
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, password=password)
        stdout_write(style.SUCCESS(f"Superuser '{username}' created successfully."))
    else:
        stdout_write(style.WARNING(f"Superuser '{username}' already exists."))


def run_create_consumer_user(stdout_write, style):
    User = get_user_model()
    username = "consumidor"
    password = "consumidor"
    ensure_role_groups()
    group = get_role_group(ROLE_CONTENT_CONSUMER)
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_staff": False, "is_superuser": False},
    )
    if created:
        user.set_password(password)
        user.save()
        stdout_write(style.SUCCESS(f"User '{username}' created (password: {password})."))
    else:
        stdout_write(style.WARNING(f"User '{username}' already exists."))
    if not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)
        stdout_write(style.SUCCESS(f"Role '{group.name}' assigned to '{username}'."))
    else:
        stdout_write(style.WARNING(f"User '{username}' already has role '{group.name}'."))



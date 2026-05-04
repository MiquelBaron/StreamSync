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
    PlataformManager,
    Serie,
    Visualization,
)
from ss.roles import (
    ROLE_CONTENT_CONSUMER,
    ROLE_DEFINITIONS,
    ROLE_PLATFORM_MANAGER,
    ensure_role_groups,
    get_role_group,
)


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


def run_create_platform_manager_user(stdout_write, style):
    username = "gestor"
    password = "gestor"
    ensure_role_groups()
    platform = Platform.objects.order_by("pk").first()
    if not platform:
        stdout_write(style.WARNING("No hi ha cap plataforma; no es crea l'usuari gestor."))
        return
    group = get_role_group(ROLE_PLATFORM_MANAGER)
    existing = PlataformManager.objects.filter(username=username).first()
    if existing:
        stdout_write(style.WARNING(f"User '{username}' (gestor) already exists."))
        if not existing.groups.filter(pk=group.pk).exists():
            existing.groups.add(group)
            stdout_write(style.SUCCESS(f"Role '{group.name}' assigned to '{username}'."))
        return
    pm = PlataformManager(
        platform=platform,
        username=username,
        is_staff=False,
        is_superuser=False,
    )
    pm.set_password(password)
    pm.save()
    pm.groups.add(group)
    stdout_write(
        style.SUCCESS(
            f"Gestor '{username}' creat (contrasenya: {password}) a la plataforma '{platform.name}'."
        )
    )


def run_populate_demo_visualizations(stdout_write, style):
    from random import choice

    User = get_user_model()
    contents: list = []
    for model in (Film, Serie):
        qs = (
            model.objects.prefetch_related("platforms")
            .filter(platforms__isnull=False)
            .distinct()
        )
        contents.extend(list(qs))
    if not contents:
        stdout_write(
            style.WARNING(
                "Cap pel·lícula o sèrie amb plataformes: executa sync_catalog abans o omet visualitzacions."
            )
        )
        return

    for idx in range(3):
        demo_name = f"viewer_demo_{idx}"
        u, created = User.objects.get_or_create(
            username=demo_name,
            defaults={"is_staff": False, "is_superuser": False},
        )
        if created:
            u.set_password("viewer_demo")
            u.save()
            stdout_write(style.SUCCESS(f"Usuari demo '{demo_name}' creat (contrasenya: viewer_demo)."))

    users = list(
        User.objects.filter(is_superuser=False).exclude(username__in=["admin", "gestor"])
    )
    if not users:
        stdout_write(style.WARNING("Cap usuari per generar visualitzacions."))
        return

    base_ts = timezone.now()
    n = 0
    for i in range(120):
        user = choice(users)
        content = choice(contents)
        platforms = list(content.platforms.all())
        if not platforms:
            continue
        platform = choice(platforms)
        viewed_at = base_ts - timedelta(seconds=i + 1, microseconds=(i * 7919) % 999_999)
        Visualization.objects.create(
            user=user,
            viewed_at=viewed_at,
            content=content,
            genre_id=content.genre_id,
            platform=platform,
        )
        n += 1
    stdout_write(style.SUCCESS(f"S'han creat {n} visualitzacions demo."))



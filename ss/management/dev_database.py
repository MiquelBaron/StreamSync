"""
Pasos reutilizables para preparar la base de datos de desarrollo.
prepare_dev_database, populate_db y comandos relacionados delegan aquí.
"""
from datetime import timedelta
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from ss.models import (
    ContentConsumer,
    Film,
    Platform,
    PlataformManager,
    Review,
    Serie,
    Visualization,
)
from ss.roles import (
    ROLE_CONTENT_CONSUMER,
    ROLE_DEFINITIONS,
    ROLE_GENERAL_DIRECTOR,
    ROLE_PLATFORM_MANAGER,
    ROLE_TECHNICAL_ADMIN,
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
    """
    Create the demo consumer as ContentConsumer from the start.

    Creating a plain User and then adding the consumer group triggers
    sync_content_consumer_profile, which calls ContentConsumer.objects.create(user_ptr_id=...).
    That can insert a second auth_user row and violate UNIQUE(username). Using ContentConsumer
    directly avoids the signal trying to create a duplicate profile.
    """
    User = get_user_model()
    username = "consumidor"
    password = "consumidor"
    ensure_role_groups()
    group = get_role_group(ROLE_CONTENT_CONSUMER)

    if ContentConsumer.objects.filter(username=username).exists():
        user = ContentConsumer.objects.get(username=username)
        stdout_write(style.WARNING(f"User '{username}' already exists."))
    else:
        User.objects.filter(username=username).delete()
        user = ContentConsumer.objects.create_user(
            username=username,
            password=password,
            is_staff=False,
            is_superuser=False,
        )
        stdout_write(style.SUCCESS(f"User '{username}' created (password: {password})."))

    if not user.groups.filter(pk=group.pk).exists():
        user.groups.add(group)
        stdout_write(style.SUCCESS(f"Role '{group.name}' assigned to '{username}'."))
    else:
        stdout_write(style.WARNING(f"User '{username}' already has role '{group.name}'."))


def run_create_technical_admin_user(stdout_write, style):
    User = get_user_model()
    username = "admin_tecnic"
    password = "devpass"
    ensure_role_groups()
    group = get_role_group(ROLE_TECHNICAL_ADMIN)
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_staff": True, "is_superuser": False},
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


def run_create_general_director_user(stdout_write, style):
    User = get_user_model()
    username = "director_general"
    password = "devpass"
    ensure_role_groups()
    group = get_role_group(ROLE_GENERAL_DIRECTOR)
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"is_staff": True, "is_superuser": False},
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


def run_create_platform_managers_for_all_platforms(stdout_write, style):
    """One PlataformManager per Platform; username gestor_<id>, password devpass."""
    ensure_role_groups()
    group = get_role_group(ROLE_PLATFORM_MANAGER)
    platforms = list(Platform.objects.order_by("pk"))
    if not platforms:
        stdout_write(style.WARNING("No hi ha cap plataforma; no es creen gestors (executa sync_catalog abans)."))
        return
    password = "devpass"
    for platform in platforms:
        username = f"gestor_{platform.pk}"
        existing = PlataformManager.objects.filter(username=username).first()
        if existing:
            if existing.platform_id != platform.pk:
                existing.platform = platform
                existing.save(update_fields=["platform"])
            if not existing.groups.filter(pk=group.pk).exists():
                existing.groups.add(group)
                stdout_write(style.SUCCESS(f"Role '{group.name}' assigned to '{username}'."))
            else:
                stdout_write(style.WARNING(f"Gestor '{username}' already exists for '{platform.name}'."))
            continue
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
                f"Gestor '{username}' creat (contrasenya: {password}) — plataforma '{platform.name}'."
            )
        )


def run_populate_dev_users(stdout_write, style):
    """Un usuari de prova per cada rol; gestors: un per plataforma (després de sync_catalog)."""
    stdout_write(style.MIGRATE_HEADING("Usuari consumidor..."))
    run_create_consumer_user(stdout_write, style)
    stdout_write(style.MIGRATE_HEADING("Usuari administrador tècnic..."))
    run_create_technical_admin_user(stdout_write, style)
    stdout_write(style.MIGRATE_HEADING("Usuari director general..."))
    run_create_general_director_user(stdout_write, style)
    stdout_write(style.MIGRATE_HEADING("Gestors de plataforma (un per plataforma)..."))
    run_create_platform_managers_for_all_platforms(stdout_write, style)


def run_populate_demo_visualizations(stdout_write, style):
    """~100 visualitzacions aleatòries (contingut, plataforma, usuari, instant)."""
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
                "Cap pel·lícula o sèrie amb plataformes: executa sync_catalog i populate_db."
            )
        )
        return

    users = list(User.objects.filter(is_superuser=False))
    if not users:
        stdout_write(style.WARNING("Cap usuari per generar visualitzacions."))
        return

    base_ts = timezone.now()
    n = 0
    for i in range(100):
        user = random.choice(users)
        content = random.choice(contents)
        platforms = list(content.platforms.all())
        if not platforms:
            continue
        platform = random.choice(platforms)
        viewed_at = base_ts - timedelta(
            seconds=i + 1,
            microseconds=random.randint(0, 999_999),
        )
        Visualization.objects.create(
            user=user,
            viewed_at=viewed_at,
            content=content,
            genre_id=content.genre_id,
            platform=platform,
        )
        n += 1
    stdout_write(style.SUCCESS(f"S'han creat {n} visualitzacions demo (aleatòries)."))


_REVIEW_TEXTS_CA = (
    "Molt bé, la recomano.",
    "Entretinguda.",
    "Bona fotografia.",
    "M'ha agradat el ritme.",
    "Final una mica fluix.",
    "Ideal per un cap de setmana.",
    "No m'ha acabat de convèncer.",
    "Guió sòlid.",
    "Curta i al gra.",
    "Es fa llarga.",
    "Actors molt encertats.",
    "Trama previsible.",
    "Vale la pena.",
    "Correcta, sense sorpreses.",
)


def run_populate_demo_film_reviews(stdout_write, style, count: int = 24):
    """Ressenyes curtes en català sobre pel·lícules (usuaris no superuser)."""
    User = get_user_model()
    films = list(Film.objects.filter(is_active=True))
    users = list(User.objects.filter(is_superuser=False))
    if not films:
        stdout_write(style.WARNING("Cap pel·lícula: omet ressenyes (sync_catalog)."))
        return
    if not users:
        stdout_write(style.WARNING("Cap usuari: omet ressenyes."))
        return

    n = 0
    for _ in range(min(count, max(1, len(films) * 4))):
        Review.objects.create(
            user=random.choice(users),
            content=random.choice(films),
            description=random.choice(_REVIEW_TEXTS_CA),
        )
        n += 1
    stdout_write(style.SUCCESS(f"S'han creat {n} ressenyes demo (pel·lícules, CA)."))

from django.contrib.auth.models import Group

ROLE_CONTENT_CONSUMER = "content_consumer"
ROLE_TECHNICAL_ADMIN = "technical_admin"
ROLE_GENERAL_DIRECTOR = "general_director"
ROLE_PLATFORM_MANAGER = "platform_manager"

ROLE_DEFINITIONS = {
    ROLE_CONTENT_CONSUMER: "Consumidor de contingut",
    ROLE_TECHNICAL_ADMIN: "Administrador tècnic",
    ROLE_GENERAL_DIRECTOR: "Director general",
    ROLE_PLATFORM_MANAGER: "Gestor de plataformes",
}


def ensure_role_groups() -> dict[str, Group]:
    groups: dict[str, Group] = {}
    for role_key, role_name in ROLE_DEFINITIONS.items():
        group, _ = Group.objects.get_or_create(name=role_name)
        groups[role_key] = group
    return groups


def get_role_group(role_key: str) -> Group:
    role_name = ROLE_DEFINITIONS[role_key]
    return Group.objects.get(name=role_name)


def user_has_role(user, role_key: str) -> bool:
    role_group = get_role_group(role_key)
    return user.groups.filter(pk=role_group.pk).exists()

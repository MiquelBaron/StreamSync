from django import template

from ss.roles import user_has_role

register = template.Library()


@register.filter
def has_role(user, role_key: str) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    try:
        return user_has_role(user, role_key)
    except Exception:
        return False

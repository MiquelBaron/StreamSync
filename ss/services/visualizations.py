from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from ss.models import Content, Visualization


def register_visualization(user, content_id: int, platform_id: int) -> Visualization:
    """
    Create a Visualization for the given content and platform.
    Raises ValueError if the platform is not linked to the content.
    """
    content = Content.objects.prefetch_related("platforms").get(pk=content_id)
    if not content.platforms.filter(pk=platform_id).exists():
        raise ValueError("La plataforma no està disponible per aquest contingut.")

    viewed_at = timezone.now()
    last_error: IntegrityError | None = None
    for bump in range(10):
        try:
            with transaction.atomic():
                return Visualization.objects.create(
                    user=user,
                    viewed_at=viewed_at,
                    content=content,
                    genre_id=content.genre_id,
                    platform_id=platform_id,
                )
        except IntegrityError as e:
            last_error = e
            viewed_at = viewed_at + timedelta(microseconds=bump + 1)
    assert last_error is not None
    raise last_error

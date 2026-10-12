"""In-app notifications. Sending never breaks the calling operation."""
import logging

from django.db import transaction

from .models import Notification

logger = logging.getLogger(__name__)


def _create(user_id, kind, title, body, ref_type, ref_id):
    try:
        Notification.objects.create(
            user_id=user_id, kind=kind, title=title[:150], body=body[:500], ref_type=ref_type, ref_id=ref_id
        )
    except Exception:  # a failed notification must never lose an order
        logger.exception("Failed to create notification")


def notify(user, kind, title, body="", ref_type="", ref_id=None):
    """Queue a notification to be written after the current transaction commits."""
    if user is None:
        return
    user_id = user.pk if hasattr(user, "pk") else user
    try:
        transaction.on_commit(lambda: _create(user_id, kind, title, body, ref_type, ref_id))
    except Exception:
        logger.exception("Failed to schedule notification")

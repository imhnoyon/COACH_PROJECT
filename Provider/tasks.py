import logging
from celery import shared_task
from django.utils import timezone
from django.db.models import Q
from Payments.models import ServiceBooking

logger = logging.getLogger(__name__)


@shared_task
def update_expired_service_bookings():
    """
    Continuously check all ServiceBooking records.
    Compare each booking's scheduled date and time with the current server time.
    If the booking date and time has already passed and the current status is not "completed",
    automatically update the booking status to "completed".
    """
    try:
        now = timezone.now()
        current_date = now.date()
        current_time = now.time()

        # Query all bookings that are expired and not completed or cancelled.
        # Exclude completed and cancelled bookings.
        # Target only records with valid booking date and time.
        expired_bookings = ServiceBooking.objects.filter(
            Q(booking_date__isnull=False) & Q(booking_time__isnull=False)
        ).exclude(
            status__in=["completed", "cancelled"]
        ).filter(
            Q(booking_date__lt=current_date) |
            Q(booking_date=current_date, booking_time__lt=current_time)
        )

        # Update the matched bookings using update() for efficiency and scalability (bulk update).
        # We explicitly update updated_at since QuerySet.update() bypasses the auto_now field save logic.
        updated_count = expired_bookings.update(status="completed", updated_at=now)

        # Log the number of bookings updated
        logger.info(f"Successfully auto-completed {updated_count} expired service booking(s).")
        return updated_count

    except Exception as e:
        logger.exception("An error occurred while automatically updating expired service bookings: %s", str(e))
        return 0

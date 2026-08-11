import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class CancellationPolicyService:
    """
    Centralized service to evaluate booking cancellation eligibility based on the service's cancellation policy.

    Policies:
    1. flexible:
       - Allowed any time before the scheduled session start datetime (now < start_time).
       - No minimum notice period required.
    2. standard:
       - Allowed only if requested at least 6 hours (or settings.STANDARD_CANCELLATION_NOTICE_HOURS) before the scheduled session start datetime.
    3. strict:
       - Never allowed once the booking has been confirmed/created.
    4. default:
       - Allowed if requested at least the configured platform hours in settings.py (default: 5 hours) before the scheduled session start datetime.
    """

    @classmethod
    def get_platform_default_hours(cls) -> int:
        """
        Retrieves the platform default cancellation notice hours directly from settings.py (default: 5).
        """
        return getattr(settings, 'DEFAULT_CANCELLATION_NOTICE_HOURS', 5)

    @classmethod
    def get_standard_hours(cls) -> int:
        """
        Retrieves standard cancellation notice hours directly from settings.py (default: 6).
        """
        return getattr(settings, 'STANDARD_CANCELLATION_NOTICE_HOURS', 6)

    @classmethod
    def validate_cancellation(cls, booking) -> tuple[bool, str]:
        """
        Validates whether the given ServiceBooking is eligible for cancellation according to its service's policy.
        
        Returns:
            (is_allowed: bool, message: str)
            - is_allowed: True if cancellation is permitted, False otherwise.
            - message: Descriptive error message if not allowed, empty string if allowed.
        """
        service = getattr(booking, 'service', None)
        if not service:
            return False, "Only service bookings can be cancelled."

        policy = getattr(service, 'cancellation_policy', 'default')

        # 1. STRICT Policy: Never allowed
        if policy == 'strict':
            return False, "This service operates under a 'Strict' cancellation policy and cannot be cancelled once booked."

        # Validate that booking date and time are present
        if not booking.booking_date or not booking.booking_time:
            return False, "Booking scheduled date or time is missing."

        # Construct scheduled session start datetime
        scheduled_dt = datetime.combine(booking.booking_date, booking.booking_time)
        if getattr(settings, 'USE_TZ', False):
            scheduled_dt = timezone.make_aware(scheduled_dt, timezone.get_current_timezone())

        now = timezone.now() if getattr(settings, 'USE_TZ', False) else datetime.now()

        # Check if booking start time has already passed or started
        if scheduled_dt <= now:
            return False, "Cannot cancel a booking that has already started or whose scheduled time has passed."

        time_remaining = scheduled_dt - now

        # 2. FLEXIBLE Policy: Allowed any time before start
        if policy == 'flexible':
            return True, ""

        # 3. STANDARD Policy: At least 6 hours notice
        elif policy == 'standard':
            standard_hours = cls.get_standard_hours()
            if time_remaining < timedelta(hours=standard_hours):
                return False, (
                    f"Under the 'Standard' cancellation policy, cancellations must be made at least "
                    f"{standard_hours} hours before the scheduled session."
                )
            return True, ""

        # 4. DEFAULT / Platform Default Policy: At least configured platform hours in settings.py (default: 5 hours)
        elif policy == 'default':
            default_hours = cls.get_platform_default_hours()
            if time_remaining < timedelta(hours=default_hours):
                return False, (
                    f"Under the platform default cancellation policy, cancellations must be made at least "
                    f"{default_hours} hours before the scheduled session."
                )
            return True, ""

        # Fallback for any unknown policy
        default_hours = cls.get_platform_default_hours()
        if time_remaining < timedelta(hours=default_hours):
            return False, (
                f"Cancellations must be made at least {default_hours} hours before the scheduled session."
            )
        return True, ""

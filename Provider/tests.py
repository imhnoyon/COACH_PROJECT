from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from Authentication.models import User
from Administration.models import Category
from Provider.models import Service, CoachProfile
from Payments.models import ServiceBooking
from Provider.tasks import update_expired_service_bookings


class ServiceBookingExpiryTaskTests(TestCase):

    def setUp(self):
        # Create users
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="password123",
            full_name="John Customer",
            role="User"
        )
        self.provider_user = User.objects.create_user(
            email="provider@example.com",
            password="password123",
            full_name="Jane Coach",
            role="Provider"
        )

        # Create Category
        self.category = Category.objects.create(name="Fitness", is_active=True)

        # Create Coach Profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.provider_user,
            about="Fitness Coach",
            is_completed=True,
            status="approved"
        )

        # Create Service
        self.service = Service.objects.create(
            coach=self.provider_user,
            title="Weight Loss Plan",
            category=self.category,
            description="Losing weight fast",
            service_type="one_time",
            session_format="video",
            session_duration=60,
            price=Decimal("100.00"),
            currency="USD",
            status="published"
        )

    def test_update_expired_service_bookings(self):
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        two_hours_ago = now - timedelta(hours=2)
        two_hours_later = now + timedelta(hours=2)

        # 1. Booking scheduled yesterday (pending) -> should become completed
        b1 = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date=yesterday.date(),
            booking_time=yesterday.time(),
            amount=Decimal("100.00"),
            currency="USD",
            status="pending",
            payment_status="pending"
        )

        # 2. Booking scheduled today, 2 hours ago (confirmed) -> should become completed
        b2 = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date=two_hours_ago.date(),
            booking_time=two_hours_ago.time(),
            amount=Decimal("100.00"),
            currency="USD",
            status="confirmed",
            payment_status="paid"
        )

        # 3. Booking scheduled today, 2 hours later (pending) -> should remain pending
        b3 = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date=two_hours_later.date(),
            booking_time=two_hours_later.time(),
            amount=Decimal("100.00"),
            currency="USD",
            status="pending",
            payment_status="pending"
        )

        # 4. Booking scheduled yesterday, but status is cancelled -> should remain cancelled
        b4 = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date=yesterday.date(),
            booking_time=yesterday.time(),
            amount=Decimal("100.00"),
            currency="USD",
            status="cancelled",
            payment_status="pending"
        )

        # 5. Booking scheduled yesterday, but status is completed -> should remain completed
        b5 = ServiceBooking.objects.create(
            user=self.customer,
            coach=self.provider_user,
            service=self.service,
            booking_date=yesterday.date(),
            booking_time=yesterday.time(),
            amount=Decimal("100.00"),
            currency="USD",
            status="completed",
            payment_status="paid"
        )

        # Execute the task
        updated_count = update_expired_service_bookings()

        # Check return value (should be 2 bookings updated)
        self.assertEqual(updated_count, 2)

        # Refresh from database and check statuses
        b1.refresh_from_db()
        b2.refresh_from_db()
        b3.refresh_from_db()
        b4.refresh_from_db()
        b5.refresh_from_db()

        self.assertEqual(b1.status, "completed")
        self.assertEqual(b2.status, "completed")
        self.assertEqual(b3.status, "pending")
        self.assertEqual(b4.status, "cancelled")
        self.assertEqual(b5.status, "completed")

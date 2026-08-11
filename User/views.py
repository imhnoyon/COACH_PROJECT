import os
import logging
import stripe
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView, Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from django.db.models.functions import Coalesce
from Provider.serializers import *
from Provider.models import *
from User.models import CoachRating, AppRating
from .serializers import *
from utils.api_response import APIResponse

from Payments.models import ServiceBooking, PaymentTransaction

logger = logging.getLogger(__name__)
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None) or os.environ.get('STRIPE_SECRET_KEY')

class PostCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return APIResponse.success(
            message="Post created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )
              
        
class CoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coach_profiles = CoachProfile.objects.filter(status="approved")\
            .annotate(avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0))\
            .order_by('-avg_rating')\
            .select_related('user')\
            .prefetch_related('categories')
        serializer = CoachProfileSerializer(coach_profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Coach profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class RecommendedCoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coach_profiles = CoachProfile.objects.filter(status="approved")\
            .annotate(avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0))\
            .order_by('-avg_rating')\
            .select_related('user')\
            .prefetch_related('categories')
        serializer = CoachProfileSerializer(coach_profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Coach profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )



class CategoryListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):


        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return APIResponse.success(
            message="Categories retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class CoachRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, coach_id):
        coach_profile = CoachProfile.objects.filter(id=coach_id).first()
        if not coach_profile:
            return APIResponse.error(
                message="Coach profile not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Enforce that the user has a completed booking with the coach
        has_completed_booking = ServiceBooking.objects.filter(
            user=request.user,
            coach=coach_profile.user,
            status="completed"
        ).exists()

        if not has_completed_booking:
            return APIResponse.error(
                message="You can only review this coach after completing a booking with them.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Enforce that the user can review only once per coach
        if CoachRating.objects.filter(coach_id=coach_id, user=request.user).exists():
            return APIResponse.error(
                message="You have already submitted a review for this coach.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        data['coach'] = coach_id

        serializer = CoachRatingSerializer(data=data)

        if serializer.is_valid():
            serializer.save(user=request.user)

            return APIResponse.success(
                message="Rating submitted successfully.",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        return APIResponse.error(
            message="Invalid data.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AppRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if AppRating.objects.filter(user=request.user).exists():
            return APIResponse.error(
                message="You have already submitted a rating for this app.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = AppRatingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return APIResponse.success(
                message="App rating submitted successfully.",
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        return APIResponse.error(
            message="Invalid data.",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AppRatingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_ratings = AppRating.objects.all()
        serializer = AppRatinglistSerializer(app_ratings, many=True, context={'request': request})
        return APIResponse.success(
            message="App ratings retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

class CoachProfileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, coach_id):
        coach_profile = CoachProfile.objects.filter(id=coach_id, status="approved")\
            .annotate(avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0))\
            .select_related('user')\
            .prefetch_related('categories', 'certifications', 'qualifications')\
            .first()

        if not coach_profile:
            return APIResponse.error(
                message="Coach profile not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = CoachProfileDetailSerializer(coach_profile, context={'request': request})
        return APIResponse.success(
            message="Coach profile details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class RecommendedCoachProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        coach_profiles = CoachProfile.objects.filter(status="approved")\
            .annotate(
                avg_rating=Coalesce(Avg('coach_ratings__rating'), 0.0),
                completed_sessions_count=Count('user__received_bookings', filter=Q(user__received_bookings__status='completed'))
            )\
            .order_by('-avg_rating', '-completed_sessions_count')\
            .select_related('user')\
            .prefetch_related('categories')

        serializer = CoachProfileSerializer(coach_profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Recommended coach profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class BlogListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        category = request.query_params.get('category', None)
        if category:
            if category.isdigit():
                blogs = Blog.objects.filter(status="published", category__id=int(category))
            else:
                blogs = Blog.objects.filter(status="published", category__name__iexact=category)
        else:
            blogs = Blog.objects.filter(status="published")

        blogs = blogs.select_related('category', 'coach', 'coach__coach_profile')
        serializer = UserBlogSerializer(blogs, many=True, context={'request': request})
        return APIResponse.success(
            message="Blogs retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class BlogDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, blog_id):
        try:
            blog = Blog.objects.select_related('category', 'coach', 'coach__coach_profile').get(id=blog_id, status="published")
        except Blog.DoesNotExist:
            return APIResponse.error(
                message="Blog not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = UserBlogSerializer(blog, context={'request': request})
        return APIResponse.success(
            message="Blog details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
class DigitalProductListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        digital_products = Product.objects.filter(status="published").select_related('category', 'coach', 'coach__coach_profile')
        serializer = DigitalProductSerializer(digital_products, many=True, context={'request': request})
        return APIResponse.success(
            message="Digital products retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class DigitalProductDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id):
        try:
            product = Product.objects.select_related('category', 'coach', 'coach__coach_profile').get(id=product_id, status="published")
        except Product.DoesNotExist:
            return APIResponse.error(
                message="Product not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = DigitalProductDetailsSerializer(product, context={'request': request})
        return APIResponse.success(
            message="Digital product details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
class UserServiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        services = Service.objects.filter(status="published").select_related('coach', 'coach__coach_profile').prefetch_related('benefits')
        serializer = userServiceCreateSerializer(services, many=True, context={'request': request})
        return APIResponse.success(
            message="Services retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
class UserServiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, service_id):
        try:
            service = Service.objects.select_related('coach', 'coach__coach_profile').prefetch_related('benefits').get(id=service_id, status="published")
        except Service.DoesNotExist:
            return APIResponse.error(
                message="Service not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = userServiceDetailsSerializer(service, context={'request': request})
        return APIResponse.success(
            message="Service details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        


class BookingServicesListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status', None) or request.query_params.get('status_filter', None)
        
        bookings = ServiceBooking.objects.filter(
            user=request.user,
            service__isnull=False,
            payment_status="paid"
        )
        
        if status_filter:
            bookings = bookings.filter(status=status_filter)
            
        bookings = bookings.select_related('service', 'service__category', 'service__coach').order_by('-id')

        serializer = BookingServicesSerializer(
            bookings,
            many=True,
            context={'request': request}
        )

        return APIResponse.success(
            message="User bookings retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class BookingDetailsSerializerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        try:
            booking = ServiceBooking.objects.select_related('service', 'service__category', 'service__coach').get(
                id=booking_id,
                user=request.user,
                service__isnull=False
            )
        except ServiceBooking.DoesNotExist:
            return APIResponse.error(
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = BookingServicesSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Booking details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class BookingRescheduleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        return self._reschedule(request, booking_id)

    def patch(self, request, booking_id):
        return self._reschedule(request, booking_id)

    def _reschedule(self, request, booking_id):
        try:
            booking = ServiceBooking.objects.select_related('coach', 'service').get(id=booking_id, user=request.user)
        except ServiceBooking.DoesNotExist:
            return APIResponse.error(
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not booking.service:
            return APIResponse.error(
                message="Only service session bookings can be rescheduled.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if booking.status in ["completed", "cancelled", "rejected"]:
            return APIResponse.error(
                message=f"Cannot reschedule a booking that is already {booking.status}.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if getattr(booking, 'is_rescheduled', False):
            return APIResponse.error(
                message="This booking has already been rescheduled once. Further rescheduling is not allowed.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Check reschedule cutoff hours from settings
        reschedule_hours = getattr(settings, 'RESHEDULED_BOOKING_TIME', 6)
        if booking.booking_date and booking.booking_time:
            current_schedule_dt = datetime.combine(booking.booking_date, booking.booking_time)
            if getattr(settings, 'USE_TZ', False):
                current_schedule_dt = timezone.make_aware(current_schedule_dt, timezone.get_current_timezone())

            now = timezone.now() if getattr(settings, 'USE_TZ', False) else datetime.now()

            if current_schedule_dt <= now:
                return APIResponse.error(
                    message="Cannot reschedule a booking whose scheduled time has already passed.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            time_remaining = current_schedule_dt - now
            if time_remaining < timedelta(hours=reschedule_hours):
                return APIResponse.error(
                    message=f"Bookings can only be rescheduled at least {reschedule_hours} hours before the scheduled time.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        serializer = BookingRescheduleSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        new_date = serializer.validated_data['booking_date']
        new_time = serializer.validated_data['booking_time']

        # Check if the requested date and time are the same as current schedule
        if booking.booking_date == new_date and booking.booking_time == new_time:
            return APIResponse.error(
                message="The requested date and time are the same as your current schedule. Please choose a different date or time.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Check that new schedule is in the future
        new_schedule_dt = datetime.combine(new_date, new_time)
        if getattr(settings, 'USE_TZ', False):
            new_schedule_dt = timezone.make_aware(new_schedule_dt, timezone.get_current_timezone())

        now = timezone.now() if getattr(settings, 'USE_TZ', False) else datetime.now()
        if new_schedule_dt <= now:
            return APIResponse.error(
                message="The new booking date and time must be in the future.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Check if the coach already has another active booking at that date and time
        conflict_exists = ServiceBooking.objects.filter(
            coach=booking.coach,
            booking_date=new_date,
            booking_time=new_time
        ).exclude(id=booking.id)\
         .exclude(status__in=['cancelled', 'rejected'])\
         .exclude(payment_status='failed')\
         .exists()

        if conflict_exists:
            return APIResponse.error(
                message="This time slot is already booked for this coach. Please choose another date or time.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        booking.booking_date = new_date
        booking.booking_time = new_time
        booking.is_rescheduled = True
        booking.save()

        res_serializer = BookingServicesSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Booking rescheduled successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )


class BookingCancelAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        return self._cancel(request, booking_id)

    def patch(self, request, booking_id):
        return self._cancel(request, booking_id)

    def _cancel(self, request, booking_id):
        try:
            with transaction.atomic():
                try:
                    booking = ServiceBooking.objects.select_for_update().select_related('coach', 'service').get(
                        id=booking_id,
                        user=request.user
                    )
                except ServiceBooking.DoesNotExist:
                    return APIResponse.error(
                        message="Booking not found.",
                        status_code=status.HTTP_404_NOT_FOUND
                    )

                if not booking.service or booking.product_id is not None:
                    return APIResponse.error(
                        message="Only service bookings can be cancelled.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                if booking.status == "cancelled":
                    return APIResponse.error(
                        message="This booking is already cancelled.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                if booking.status == "completed":
                    return APIResponse.error(
                        message="Cannot cancel a completed booking.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                if booking.status == "rejected":
                    return APIResponse.error(
                        message="This booking has already been rejected.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                if booking.payment_status == "refunded" or booking.refund_status == "completed" or booking.refund_id:
                    return APIResponse.error(
                        message="This booking has already been refunded.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                # Evaluate cancellation policy rules (flexible, standard, strict, default)
                from Payments.cancellation_policy import CancellationPolicyService
                is_allowed, error_message = CancellationPolicyService.validate_cancellation(booking)
                if not is_allowed:
                    return APIResponse.error(
                        message=error_message,
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                # If payment was completed ("paid"), trigger Stripe refund
                if booking.payment_status == "paid":
                    payment_tx = PaymentTransaction.objects.filter(booking=booking).first()
                    if payment_tx and payment_tx.stripe_payment_intent_id:
                        from Payments.stripe_refund import StripeRefundService
                        StripeRefundService.refund_booking(
                            booking,
                            new_status="cancelled",
                            description=f"Refund debit for cancelled booking #{booking.id}"
                        )
                    else:
                        booking.payment_status = "refunded"
                        booking.refund_status = "completed"
                        booking.refunded_at = timezone.now()
                        booking.status = "cancelled"
                        booking.save()
                else:
                    booking.status = "cancelled"
                    booking.save()

            res_serializer = BookingServicesSerializer(booking, context={"request": request})
            return APIResponse.success(
                message="Booking successfully cancelled and amount refunded to your account.",
                data=res_serializer.data,
                status_code=status.HTTP_200_OK
            )

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Stripe InvalidRequestError during cancellation of booking {booking_id}: {str(e)}")
            return APIResponse.error(
                message=f"Refund failed: Invalid request: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.CardError as e:
            logger.error(f"Stripe CardError during cancellation of booking {booking_id}: {str(e)}")
            return APIResponse.error(
                message=f"Refund failed: Card declined: {e.user_message or str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except stripe.error.APIConnectionError as e:
            logger.error(f"Stripe APIConnectionError during cancellation of booking {booking_id}: {str(e)}")
            return APIResponse.error(
                message="Refund failed: Stripe network connectivity issue.",
                status_code=status.HTTP_502_BAD_GATEWAY
            )
        except stripe.error.RateLimitError as e:
            logger.error(f"Stripe RateLimitError during cancellation of booking {booking_id}: {str(e)}")
            return APIResponse.error(
                message="Refund failed: Stripe rate limit exceeded.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except stripe.error.StripeError as e:
            logger.error(f"StripeError during cancellation of booking {booking_id}: {str(e)}")
            return APIResponse.error(
                message=f"Stripe refund failed: {e.user_message or str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during cancellation of booking {booking_id}: {str(e)}")
            return APIResponse.error(
                message=f"An unexpected error occurred: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
            
class UserProductsListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user_products = ServiceBooking.objects.filter(
            user=request.user,
            product__isnull=False,
            payment_status="paid"
        ).select_related('product', 'product__category', 'product__coach', 'product__coach__coach_profile').order_by('-id')

        serializer = ProductBuyinglistSerializer(
            user_products,
            many=True,
            context={'request': request}
        )

        return APIResponse.success(
            message="User purchased products retrieved successfully.",
            data=serializer.data,
        )
        
        
        
class UserproductDetailsSerializerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        try:
            booking = ServiceBooking.objects.select_related('product', 'product__category', 'product__coach', 'product__coach__coach_profile').get(
                id=booking_id,
                user=request.user,
                product__isnull=False
            )
        except ServiceBooking.DoesNotExist:
            return APIResponse.error(
                message="Product booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductBuyinglistSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Product booking details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
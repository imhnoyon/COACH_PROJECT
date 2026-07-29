from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from utils.api_response import APIResponse

from .models import ServiceBooking
from .serializers import (
    ServiceBookingCreateSerializer,
    ServiceBookingDetailSerializer
)


class ServiceBookingCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        """Order/Book a service with date, time, and session details."""
        serializer = ServiceBookingCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        booking = serializer.save()
        res_serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Service order created successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def get(self, request):
        """Retrieve list of service orders / bookings for the authenticated user or coach."""
        if getattr(request.user, 'role', None) == 'Provider':
            bookings = ServiceBooking.objects.filter(coach=request.user)\
                .select_related('user', 'coach', 'service', 'service__category')
        else:
            bookings = ServiceBooking.objects.filter(user=request.user)\
                .select_related('user', 'coach', 'service', 'service__category')

        serializer = ServiceBookingDetailSerializer(bookings, many=True, context={'request': request})
        return APIResponse.success(
            message="Service orders retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class ServiceBookingDetailView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self, booking_id, user):
        try:
            return ServiceBooking.objects.select_related('user', 'coach', 'service', 'service__category').get(
                id=booking_id
            )
        except ServiceBooking.DoesNotExist:
            return None

    def get(self, request, booking_id):
        """Retrieve details of a specific service order / booking."""
        booking = self.get_object(booking_id, request.user)
        if not booking:
            return APIResponse.error(
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if booking.user != request.user and booking.coach != request.user:
            return APIResponse.error(
                message="You do not have permission to view this booking.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Booking details retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def patch(self, request, booking_id):
        """Update status or payment status of a booking."""
        booking = self.get_object(booking_id, request.user)
        if not booking:
            return APIResponse.error(
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if booking.user != request.user and booking.coach != request.user:
            return APIResponse.error(
                message="You do not have permission to modify this booking.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        allowed_fields = ['status', 'payment_status', 'payment_method', 'transaction_id', 'notes']
        update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

        for attr, val in update_data.items():
            setattr(booking, attr, val)
        booking.save()

        res_serializer = ServiceBookingDetailSerializer(booking, context={'request': request})
        return APIResponse.success(
            message="Booking updated successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )

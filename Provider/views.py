import json
from django.db import transaction
from django.db.migrations import serializer
from rest_framework import request, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from utils.permissions import IsProviderUser
from Administration.models import Category
from Administration.serializers import CategorySerializer
from utils.api_response import APIResponse

from .models import CoachProfile, Certification, Qualification
from .serializers import *


class CategoryListView(APIView):
    def get(self, request):
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return APIResponse.success(
            message="Categories retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class CoachProfileView(APIView):
    permission_classes = [IsAuthenticated,IsProviderUser]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self, user):
        return CoachProfile.objects.filter(user=user)\
            .select_related('user')\
            .prefetch_related('categories', 'certifications', 'qualifications')\
            .first()

    def get(self, request):
        profile = self.get_queryset(request.user)
        if not profile:
            return APIResponse.error(
                message="Coach profile not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = CoachProfileDetailSerializer(profile, context={'request': request})
        return APIResponse.success(
            message="Coach profile retrieved successfully.",
            data=serializer.data
        )

    def post(self, request):
        """Create or update coach profile with photo, about, categories & certificates."""
        # 1. Parse category_ids from request
        category_ids = request.POST.getlist('category_ids') or request.POST.getlist('category_ids[]')

        # 2. Validate request data
        serializer = CreateCoachProfileSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 3. Save profile and related models atomically
        with transaction.atomic():
            profile, created = CoachProfile.objects.update_or_create(
                user=request.user,
                defaults={
                    'about': serializer.validated_data['about'],
                    'profile_photo': serializer.validated_data['profile_photo'],
                    'introduction_video': serializer.validated_data.get('introduction_video'),
                    'expertises': serializer.validated_data.get('expertises', []),
                    'is_completed': True,
                }
            )

            # Assign categories
            if category_ids:
                profile.categories.set(category_ids)

            # Save certifications and qualifications
            self._save_certifications(request, profile)
            self._save_qualifications(request, profile)

        # 4. Fetch fresh optimized profile & return response
        updated_profile = self.get_queryset(request.user)
        res_serializer = CoachProfileDetailSerializer(updated_profile, context={'request': request})

        msg = "Coach profile created successfully." if created else "Coach profile updated successfully."
        return APIResponse.success(
            message=msg,
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def patch(self, request):
        """Update coach profile fields (partial or full) at the same endpoint."""
        profile = self.get_queryset(request.user)
        if not profile:
            return APIResponse.error(
                message="Coach profile not found. Create profile first.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        category_ids = request.POST.getlist('category_ids') or request.POST.getlist('category_ids[]')

        serializer = CreateCoachProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            serializer.save()

            if category_ids:
                profile.categories.set(category_ids)

            if any('certification' in k for k in request.POST) or any('certification' in k for k in request.FILES):
                self._save_certifications(request, profile)

            if any('qualification' in k for k in request.POST) or any('qualification' in k for k in request.FILES):
                self._save_qualifications(request, profile)

        updated_profile = self.get_queryset(request.user)
        res_serializer = CoachProfileDetailSerializer(updated_profile, context={'request': request})
        return APIResponse.success(
            message="Coach profile updated successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )

    def _save_certifications(self, request, profile):
        """Helper method to parse and save certifications."""
        names = request.POST.getlist('certification_names') or request.POST.getlist('certifications_name')
        docs = request.FILES.getlist('certification_documents') or request.FILES.getlist('certifications_document')

        # Check indexed format (certifications[0][name], certifications[0][document])
        idx = 0
        items = []
        while f'certifications[{idx}][name]' in request.POST:
            name = request.POST.get(f'certifications[{idx}][name]')
            doc = request.FILES.get(f'certifications[{idx}][document]')
            if name and doc:
                items.append((name, doc))
            idx += 1

        if items:
            profile.certifications.all().delete()
            for name, doc in items:
                Certification.objects.create(coach=profile, name=name, document=doc)
        elif names and docs:
            profile.certifications.all().delete()
            for name, doc in zip(names, docs):
                Certification.objects.create(coach=profile, name=name, document=doc)

    def _save_qualifications(self, request, profile):
        """Helper method to parse and save qualifications."""
        names = request.POST.getlist('qualification_names') or request.POST.getlist('qualifications_name')
        docs = request.FILES.getlist('qualification_documents') or request.FILES.getlist('qualifications_document')

        # Check indexed format (qualifications[0][name], qualifications[0][document])
        idx = 0
        items = []
        while f'qualifications[{idx}][name]' in request.POST:
            name = request.POST.get(f'qualifications[{idx}][name]')
            doc = request.FILES.get(f'qualifications[{idx}][document]')
            if name and doc:
                items.append((name, doc))
            idx += 1

        if items:
            profile.qualifications.all().delete()
            for name, doc in items:
                Qualification.objects.create(coach=profile, name=name, document=doc)
        elif names and docs:
            profile.qualifications.all().delete()
            for name, doc in zip(names, docs):
                Qualification.objects.create(coach=profile, name=name, document=doc)

class CoachProfileListView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        """Retrieve all incomplete coach/provider profiles (is_completed=False)."""
        profiles = CoachProfile.objects.select_related('user')\
            .prefetch_related('categories', 'certifications', 'qualifications')\
            .filter(status='pending')
        serializer = CoachProfileDetailSerializer(profiles, many=True, context={'request': request})
        return APIResponse.success(
            message="Incomplete provider profiles retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def patch(self, request, profile_id):
        """
        Update coach profile status (approved/rejected)
        or mark it as completed.
        """

        try:
            profile = CoachProfile.objects.get(id=profile_id)
        except CoachProfile.DoesNotExist:
            return APIResponse.error(
                message="Coach profile not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get("action")  # approved | rejected |

        if action == "approved":
            if profile.status != "pending":
                return APIResponse.error(
                    message="Only pending profiles can be approved.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            profile.status = "approved"
            profile.save()
            message = "Coach profile approved successfully."
        elif action == "rejected":
            if profile.status != "pending":
                return APIResponse.error(
                    message="Only pending profiles can be rejected.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            profile.status = "rejected"
            profile.save()
            message = "Coach profile rejected successfully."
        else:
            return APIResponse.error(
                message="Invalid action. Use 'approved', 'rejected'",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        serializer = CoachProfileDetailSerializer(
            profile,
            context={"request": request}
        )
        return APIResponse.success(
            message=message,
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class ServiceCreateView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = ServiceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            service = serializer.save(coach=request.user)

            # Handle benefits list (supports JSON list or form-data)
            benefits_data = request.data.get('benefits') or request.POST.getlist('benefits') or request.POST.getlist('benefits[]')
            if isinstance(benefits_data, str):
                try:
                    benefits_data = json.loads(benefits_data)
                except Exception:
                    benefits_data = [x.strip() for x in benefits_data.split(',') if x.strip()]

            if isinstance(benefits_data, list):
                for item in benefits_data:
                    outcome_text = item.get('outcome') if isinstance(item, dict) else str(item)
                    if outcome_text and outcome_text.strip():
                        ClientBenefit.objects.create(service=service, outcome=outcome_text.strip())

        # Prefetch related benefits for serialized response
        updated_service = Service.objects.prefetch_related('benefits').get(id=service.id)
        res_serializer = ServiceCreateSerializer(updated_service, context={'request': request})
        return APIResponse.success(
            message="Service created successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )
        
        
    def patch(self, request, service_id):
        """Update an existing service."""
        try:
            service = Service.objects.get(id=service_id, coach=request.user)
        except Service.DoesNotExist:
            return APIResponse.error(
                message="Service not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ServiceCreateSerializer(service, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            serializer.save()

            # Handle benefits update
            benefits_data = request.data.get('benefits') or request.POST.getlist('benefits') or request.POST.getlist('benefits[]')
            if isinstance(benefits_data, str):
                try:
                    benefits_data = json.loads(benefits_data)
                except Exception:
                    benefits_data = [x.strip() for x in benefits_data.split(',') if x.strip()]

            if isinstance(benefits_data, list):
                service.benefits.all().delete()
                for item in benefits_data:
                    outcome_text = item.get('outcome') if isinstance(item, dict) else str(item)
                    if outcome_text and outcome_text.strip():
                        ClientBenefit.objects.create(service=service, outcome=outcome_text.strip())

        updated_service = Service.objects.prefetch_related('benefits').get(id=service.id)
        res_serializer = ServiceCreateSerializer(updated_service, context={'request': request})
        return APIResponse.success(
            message="Service updated successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
    def get(self, request, service_id):
        """Retrieve a specific service by ID."""
        try:
            service = Service.objects.prefetch_related('benefits').get(id=service_id, coach=request.user)
        except Service.DoesNotExist:
            return APIResponse.error(
                message="Service not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ServiceCreateSerializer(service, context={'request': request})
        return APIResponse.success(
            message="Service retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
 
        
class BlogCreateView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = BlogSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        blog = serializer.save(coach=request.user)

        res_serializer = BlogSerializer(blog, context={'request': request})
        return APIResponse.success(
            message="Blog created successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )
        
    def patch(self, request, blog_id):
        """Update an existing blog."""
        try:
            blog = Blog.objects.get(id=blog_id, coach=request.user)
        except Blog.DoesNotExist:
            return APIResponse.error(
                message="Blog not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = BlogSerializer(blog, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        res_serializer = BlogSerializer(blog, context={'request': request})
        return APIResponse.success(
            message="Blog updated successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
class ProductCreateView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        product = serializer.save(coach=request.user)

        res_serializer = ProductSerializer(product, context={'request': request})
        return APIResponse.success(
            message="Product created successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_201_CREATED
        )
        
    def patch(self, request, product_id):
        """Update an existing product."""
        try:
            product = Product.objects.get(id=product_id, coach=request.user)
        except Product.DoesNotExist:
            return APIResponse.error(
                message="Product not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductSerializer(product, data=request.data, partial=True)
        if not serializer.is_valid():
            return APIResponse.error(
                message="Validation error",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer.save()

        res_serializer = ProductSerializer(product, context={'request': request})
        return APIResponse.success(
            message="Product updated successfully.",
            data=res_serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
    def get(self, request, product_id):
        """Retrieve a specific product by ID."""
        try:
            product = Product.objects.get(id=product_id, coach=request.user)
        except Product.DoesNotExist:
            return APIResponse.error(
                message="Product not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductSerializer(product, context={'request': request})
        return APIResponse.success(
            message="Product retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
        
        
        
class productListView(APIView):
    permission_classes = [IsAuthenticated, IsProviderUser]

    def get(self, request):
        """Retrieve all products for the authenticated coach."""
        products = Product.objects.filter(coach=request.user)
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return APIResponse.success(
            message="Products retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
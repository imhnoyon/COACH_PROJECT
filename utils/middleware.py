from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from Provider.models import CoachProfile

class ProviderApprovalMiddleware(MiddlewareMixin):
    def process_request(self, request):
        path_lower = request.path.lower()
        if path_lower.startswith('/api/v1/provider/') or path_lower.startswith('/api/v1/provider-dashboard/'):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                try:
                    from rest_framework_simplejwt.authentication import JWTAuthentication
                    auth_res = JWTAuthentication().authenticate(request)
                    if auth_res is not None:
                        user, _ = auth_res
                except Exception:
                    pass

            if user and user.is_authenticated and getattr(user, 'role', '').lower() in ['provider', 'coach']:
                coach_profile = CoachProfile.objects.filter(user=user).first()

                # If status is rejected, block all provider endpoints
                if coach_profile and coach_profile.status == 'rejected':
                    return JsonResponse({
                        "success": False,
                        "status": 403,
                        "message": "Your provider account has been rejected."
                    }, status=403)

                # Allow coach-profile and categories-list endpoints for pending providers
                is_profile_endpoint = (
                    '/coach-profile' in path_lower 
                )

                # Block all other endpoints if not approved
                if not is_profile_endpoint:
                    if not coach_profile or coach_profile.status != 'approved':
                        return JsonResponse({
                            "success": False,
                            "status": 403,
                            "message": "Your provider account is pending for admin approval."
                        }, status=403)

from rest_framework.views import exception_handler
from rest_framework import status
from utils.api_response import APIResponse

def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes exception responses
    using the APIResponse utility.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If the exception handler returned a response (handled exception)
    if response is not None:
        # Check if the response data contains validation errors
        # (typically from DRF's serializer validation)
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            return APIResponse.error(
                message="Validation failed",
                errors=response.data,
                status_code=response.status_code
            )
        
        # Handle other types of errors (permission denied, not found, etc.)
        # If response.data is a dict with 'detail', use it as message
        message = "An error occurred"
        if isinstance(response.data, dict) and 'detail' in response.data:
            message = response.data['detail']
            # Remove detail from data if we are using it as message
            # But wait, response.data in DRF for exceptions usually is {'detail': '...'}
            # or a list/dict of errors.
            
        elif isinstance(response.data, list):
             # sometimes it returns a list of errors
             message = str(response.data[0]) 
             
        # For non-400 errors, we can also standardize
        return APIResponse.error(
            message=message,
            errors=response.data if not isinstance(response.data, dict) or 'detail' not in response.data else None,
            status_code=response.status_code
        )

    return response

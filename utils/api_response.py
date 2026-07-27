from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import exception_handler
class APIResponse:
    """
    Standardized API Response Handler
    """

    @staticmethod
    def success(message="Success", data=None, status_code=status.HTTP_200_OK):
        """
        Returns a successful response.
        :param message: Success message string
        :param data: Data dictionary (optional)
        :param status_code: HTTP status code
        :return: Response object
        """
        response_data = {
            "success": True,
            "status": status_code,
            "message": message,
        }
        
        if data is not None:
            response_data["data"] = data
            
        return Response(response_data, status=status_code)

    # @staticmethod
    # def error(message="Error", errors=None, error_code=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
    #     """
    #     Returns an error response.
    #     :param message: Error message string
    #     :param errors: Detailed errors dictionary (optional)
    #     :param error_code: Application-specific error code (optional)
    #     :param status_code: HTTP status code
    #     :return: Response object
    #     """
    #     # Support 'data' as an alias for 'errors' to prevent TypeErrors
    #     if errors is None and 'data' in kwargs:
    #         errors = kwargs['data']

    #     response_data = {
    #         "success": False,
    #         "status": status_code,
    #         "message": message,
    #     }

    #     if errors:
    #         response_data["errors"] = errors
        
    #     if error_code:
    #         response_data["error_code"] = error_code

    #     return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        message="Error",
        errors=None,
        error_code=None,
        status_code=status.HTTP_400_BAD_REQUEST,
        **kwargs,
    ):
        if errors is None and "data" in kwargs:
            errors = kwargs["data"]

        # Show first field name with its error message
        if isinstance(errors, dict):
            for field, field_errors in errors.items():
                if isinstance(field_errors, (list, tuple)) and field_errors:
                    message = f"{field}! {field_errors[0]}"
                    break
                elif isinstance(field_errors, str):
                    message = f"{field}! {field_errors}"
                    break

        response_data = {
            "success": False,
            "status": status_code,
            "message": message,
        }

        if errors:
            response_data["errors"] = errors

        if error_code:
            response_data["error_code"] = error_code

        return Response(response_data, status=status_code)

    
    # @staticmethod
    # def error(message="Error", errors=None, error_code=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):

    # # Support alias
    #     if errors is None and 'data' in kwargs:
    #         errors = kwargs['data']

    #     # Extract first error cleanly, including the field name
    #     if errors:
    #         if isinstance(errors, dict):
    #             first_field = list(errors.keys())[0]
    #             first_error = list(errors.values())[0]

    #             if isinstance(first_error, list):
    #                 message = f"{first_field} {first_error[0]}"
    #             else:
    #                 message = f"{first_field} {first_error} "

    #         elif isinstance(errors, list):
    #             message = errors[0]

    #     response_data = {
    #         "success": False,
    #         "status": status_code,
    #         "message": str(message),  # convert ErrorDetail -> clean string
    #     }

    #     if error_code:
    #         response_data["error_code"] = error_code

    #     return Response(response_data, status=status_code)
    
   

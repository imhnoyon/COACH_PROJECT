from rest_framework.pagination import PageNumberPagination, Response
from utils.api_response import APIResponse
from rest_framework import status

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000

    def get_paginated_response(self, data, message="Data retrieved successfully"):
        return Response({
            "success": True,
            "status": status.HTTP_200_OK,
            "message": message,
            "total": self.page.paginator.count,
            "page": self.page.number,
            "page_size": self.get_page_size(self.request),
            "total_pages": self.page.paginator.num_pages,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "data": data,
        }, status=status.HTTP_200_OK)
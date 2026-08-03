from rest_framework import serializers
from Authentication.models import User
from Administration.models import Category
from Provider.models import CoachProfile
from .models import Post


class PostCreateSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.name", read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "category",
            "category_id",
            "title",
            "description",
            "urgency_Level",
            "day_price",
            "hours_price",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        day_price = attrs.get("day_price")
        hours_price = attrs.get("hours_price")

        if day_price is None and hours_price is None:
            raise serializers.ValidationError(
                "Either day_price or hours_price is required."
            )

        if day_price is not None and day_price <= 0:
            raise serializers.ValidationError(
                {"day_price": "Day price must be greater than 0."}
            )

        if hours_price is not None and hours_price <= 0:
            raise serializers.ValidationError(
                {"hours_price": "Hour price must be greater than 0."}
            )

        return attrs


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "email", "phone_number"]


class CoachProfileSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = CoachProfile
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
        
        


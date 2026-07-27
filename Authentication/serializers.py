from rest_framework import serializers
from .models import User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    re_password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'phone_number', 'latitude', 'longitude', 'password', 're_password']
        
        
    def validate(self, data):
        password = data.get('password')
        re_password = data.get('re_password')
        if password != re_password:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self,validated_data):
        validated_data.pop('re_password')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
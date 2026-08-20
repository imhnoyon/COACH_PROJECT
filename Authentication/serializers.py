from rest_framework import serializers
from .models import User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    re_password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role', 'phone_number', 'address', 'password', 're_password']
        
        
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
    
    
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    re_new_password = serializers.CharField(required=True)

    def validate(self, data):
        if data['new_password'] != data['re_new_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data
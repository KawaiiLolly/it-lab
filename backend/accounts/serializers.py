from django.contrib.auth.models import User
from rest_framework import serializers

class SignupSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, data):
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )

        return user
from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Profile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    full_name = serializers.CharField(max_length=150)
    roll_no = serializers.CharField(max_length=30)

    class Meta:
        model = User
        fields = ["full_name", "email", "password", "roll_no"]

    def validate_roll_no(self, value):
        if Profile.objects.filter(roll_no=value).exists():
            raise serializers.ValidationError("This roll number is already registered.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def create(self, validated_data):
        full_name = validated_data.pop("full_name")
        roll_no = validated_data.pop("roll_no")
        email = validated_data["email"]

        # Django's User model needs a username — we use the email itself, so
        # candidates never see or choose a separate username. Login also uses email.
        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
        )
        Profile.objects.create(user=user, full_name=full_name, roll_no=roll_no)
        return user


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="profile.full_name", read_only=True)
    roll_no = serializers.CharField(source="profile.roll_no", read_only=True)

    class Meta:
        model = User
        fields = ["id", "full_name", "email", "roll_no"]

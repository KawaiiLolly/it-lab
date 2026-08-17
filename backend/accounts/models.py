from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """Extra fields for a User — full name (for display) and roll number.
    Note: User.username is set to the user's email internally (see RegisterSerializer) —
    there is no separate username the candidate ever sees or picks."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=150)
    roll_no = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return f"{self.full_name} ({self.roll_no})"

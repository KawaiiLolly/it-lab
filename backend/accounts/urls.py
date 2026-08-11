from django.urls import path

from .views import SignupView, ProfileView

urlpatterns = [
    path('signup/', SignupView.as_view()),
    path('profile/', ProfileView.as_view()),
]
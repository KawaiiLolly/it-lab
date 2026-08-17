from django.urls import path
from .views import (
    StartQuizView,
    QuizStatusView,
    QuizSessionDetailView,
    SaveAnswerView,
    BookmarkView,
    SubmitQuizView,
)

urlpatterns = [
    path("start/", StartQuizView.as_view(), name="quiz-start"),
    path("status/", QuizStatusView.as_view(), name="quiz-status"),
    path("session/<int:session_id>/", QuizSessionDetailView.as_view(), name="quiz-session-detail"),
    path("session/<int:session_id>/answer/", SaveAnswerView.as_view(), name="quiz-save-answer"),
    path("session/<int:session_id>/bookmark/", BookmarkView.as_view(), name="quiz-bookmark"),
    path("session/<int:session_id>/submit/", SubmitQuizView.as_view(), name="quiz-submit"),
]

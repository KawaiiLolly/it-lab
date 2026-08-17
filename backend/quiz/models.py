from django.db import models
from django.contrib.auth.models import User

OPTION_CHOICES = [
    ("A", "Option A"),
    ("B", "Option B"),
    ("C", "Option C"),
    ("D", "Option D"),
]


class Question(models.Model):
    """A single question in the shared question bank."""
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES)

    def __str__(self):
        return self.text[:50]


class QuizSession(models.Model):
    """One attempt at the test by one user. Holds the final score once submitted."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    duration_seconds = models.PositiveIntegerField(default=1200)  # 20 minutes
    submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    total_questions = models.PositiveIntegerField(default=0)
    attempted_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    wrong_count = models.PositiveIntegerField(default=0)
    unattempted_count = models.PositiveIntegerField(default=0)
    score = models.IntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username} - session {self.id}"


class SessionQuestion(models.Model):
    """
    Links a QuizSession to a Question, in a randomized order specific to that session.
    Also stores the candidate's selected option for that question (used by Save/Clear).
    """
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="session_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    selected_option = models.CharField(max_length=1, choices=OPTION_CHOICES, null=True, blank=True)
    bookmarked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "question")
        ordering = ["order"]

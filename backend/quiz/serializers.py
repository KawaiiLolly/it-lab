from rest_framework import serializers
from .models import Question, SessionQuestion


class QuestionPublicSerializer(serializers.ModelSerializer):
    """Question shown to a candidate during the test — correct_option is never exposed."""

    class Meta:
        model = Question
        fields = ["id", "text", "option_a", "option_b", "option_c", "option_d"]


class SessionQuestionSerializer(serializers.ModelSerializer):
    question = QuestionPublicSerializer()

    class Meta:
        model = SessionQuestion
        fields = ["order", "question", "selected_option", "bookmarked"]

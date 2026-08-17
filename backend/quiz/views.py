import random

from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Question, QuizSession, SessionQuestion
from .serializers import SessionQuestionSerializer

QUESTIONS_PER_TEST = 10
TEST_DURATION_SECONDS = 20 * 60  # 20 minutes

MARKS_CORRECT = 5
MARKS_WRONG = -2
MARKS_UNATTEMPTED = 0


def _get_owned_session(user, session_id):
    """Fetch a session only if it belongs to the requesting user."""
    try:
        return QuizSession.objects.get(id=session_id, user=user)
    except QuizSession.DoesNotExist:
        return None


def _grade_session(session):
    """Grades an in-progress session and marks it submitted. Caller must ensure it isn't already submitted."""
    correct = wrong = unattempted = 0
    score = 0

    for sq in session.session_questions.select_related("question").all():
        if not sq.selected_option:
            unattempted += 1
            score += MARKS_UNATTEMPTED
        elif sq.selected_option == sq.question.correct_option:
            correct += 1
            score += MARKS_CORRECT
        else:
            wrong += 1
            score += MARKS_WRONG

    session.submitted = True
    session.submitted_at = timezone.now()
    session.attempted_count = correct + wrong
    session.correct_count = correct
    session.wrong_count = wrong
    session.unattempted_count = unattempted
    session.score = score
    session.save()

    return {
        "total_questions": session.total_questions,
        "attempted_count": session.attempted_count,
        "correct_count": correct,
        "wrong_count": wrong,
        "unattempted_count": unattempted,
        "score": score,
    }


def _expire_if_needed(session):
    """If the 20-minute window has passed and the session is still open, auto-grade it."""
    if session.submitted:
        return session
    elapsed = (timezone.now() - session.started_at).total_seconds()
    if elapsed >= session.duration_seconds:
        _grade_session(session)
    return session


class StartQuizView(APIView):
    """
    POST -> starts (or resumes) this user's ONE allowed attempt.
    - No previous session: creates one with a random subset/order of questions.
    - An in-progress session exists (not submitted, time not up): resumes it.
    - A submitted (or just-expired) session exists: refuses — only one attempt allowed.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        existing = QuizSession.objects.filter(user=request.user).order_by("-started_at").first()

        if existing is not None:
            existing = _expire_if_needed(existing)
            if existing.submitted:
                return Response(
                    {"error": "You have already attempted this test. Only one attempt is allowed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # resume the in-progress session instead of starting a new one
            return Response({
                "session_id": existing.id,
                "total_questions": existing.total_questions,
                "duration_seconds": existing.duration_seconds,
            }, status=status.HTTP_200_OK)

        all_questions = list(Question.objects.all())
        if not all_questions:
            return Response(
                {"error": "No questions available in the question bank yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Each session (and therefore each concurrent user) gets its own random
        # order, picked independently — so no two candidates see the same sequence.
        count = min(QUESTIONS_PER_TEST, len(all_questions))
        chosen = random.sample(all_questions, count)

        session = QuizSession.objects.create(
            user=request.user,
            duration_seconds=TEST_DURATION_SECONDS,
            total_questions=count,
        )

        SessionQuestion.objects.bulk_create([
            SessionQuestion(session=session, question=q, order=i + 1)
            for i, q in enumerate(chosen)
        ])

        return Response({
            "session_id": session.id,
            "total_questions": count,
            "duration_seconds": TEST_DURATION_SECONDS,
        }, status=status.HTTP_201_CREATED)


class QuizStatusView(APIView):
    """GET -> tells the dashboard/instructions page whether this user has already attempted the test."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session = QuizSession.objects.filter(user=request.user).order_by("-started_at").first()
        if session is None:
            return Response({"attempted": False, "in_progress": False})

        session = _expire_if_needed(session)
        if session.submitted:
            return Response({
                "attempted": True,
                "in_progress": False,
                "score": session.score,
                "total_questions": session.total_questions,
                "attempted_count": session.attempted_count,
            })

        return Response({"attempted": False, "in_progress": True, "session_id": session.id})


class QuizSessionDetailView(APIView):
    """GET -> the questions (in this session's fixed random order) + time remaining."""
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        session = _get_owned_session(request.user, session_id)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

        session = _expire_if_needed(session)

        elapsed = (timezone.now() - session.started_at).total_seconds()
        remaining = max(0, int(session.duration_seconds - elapsed))

        questions = session.session_questions.select_related("question").order_by("order")

        return Response({
            "session_id": session.id,
            "submitted": session.submitted,
            "remaining_seconds": remaining,
            "duration_seconds": session.duration_seconds,
            "questions": SessionQuestionSerializer(questions, many=True).data,
        })


class SaveAnswerView(APIView):
    """POST {question_id, selected_option} -> saves (or clears, if selected_option is null) the answer."""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _get_owned_session(request.user, session_id)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        if session.submitted:
            return Response({"error": "Test already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        question_id = request.data.get("question_id")
        selected_option = request.data.get("selected_option") or None

        try:
            sq = session.session_questions.get(question_id=question_id)
        except SessionQuestion.DoesNotExist:
            return Response({"error": "Question not part of this session"}, status=status.HTTP_400_BAD_REQUEST)

        sq.selected_option = selected_option
        sq.save()
        return Response({"message": "saved", "selected_option": sq.selected_option})


class BookmarkView(APIView):
    """POST {question_id, bookmarked} -> flags a question for later review within the test."""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _get_owned_session(request.user, session_id)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        if session.submitted:
            return Response({"error": "Test already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        question_id = request.data.get("question_id")
        bookmarked = bool(request.data.get("bookmarked"))

        try:
            sq = session.session_questions.get(question_id=question_id)
        except SessionQuestion.DoesNotExist:
            return Response({"error": "Question not part of this session"}, status=status.HTTP_400_BAD_REQUEST)

        sq.bookmarked = bookmarked
        sq.save()
        return Response({"message": "saved", "bookmarked": sq.bookmarked})


class SubmitQuizView(APIView):
    """POST -> grades the session, locks it, and returns the result summary."""
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _get_owned_session(request.user, session_id)
        if session is None:
            return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
        if session.submitted:
            return Response({"error": "Test already submitted"}, status=status.HTTP_400_BAD_REQUEST)

        result = _grade_session(session)
        return Response(result)

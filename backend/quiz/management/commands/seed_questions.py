from django.core.management.base import BaseCommand
from quiz.models import Question

# (question text, option A, option B, option C, option D, correct option)
QUESTIONS = [
    ("What is the capital of France?", "Paris", "London", "Rome", "Berlin", "A"),
    ("Which language runs natively in a web browser?", "Java", "C", "Python", "JavaScript", "D"),
    ("What does CPU stand for?", "Central Process Unit", "Central Processing Unit",
     "Computer Personal Unit", "Central Processor Utility", "B"),
    ("Which of these is a Python web framework?", "Django", "Laravel", "Spring", "Rails", "A"),
    ("What does SQL stand for?", "Structured Query Language", "Simple Query Language",
     "Sequential Query Language", "Standard Query Language", "A"),
    ("Which HTTP method is typically used to update a resource?", "GET", "POST", "PUT", "DELETE", "C"),
    ("What is the time complexity of binary search?", "O(n)", "O(n^2)", "O(log n)", "O(1)", "C"),
    ("Which organization maintains the Django framework?", "Google", "Django Software Foundation",
     "Microsoft", "Meta", "B"),
    ("What does JWT stand for?", "Java Web Token", "JSON Web Token", "Joint Web Token",
     "JavaScript Web Token", "B"),
    ("Which database does this project use?", "MySQL", "MongoDB", "PostgreSQL", "SQLite", "C"),
]


class Command(BaseCommand):
    help = "Seeds the question bank with 10 sample questions (run once)."

    def handle(self, *args, **options):
        if Question.objects.exists():
            self.stdout.write("Questions already exist — skipping seed.")
            return

        for text, a, b, c, d, correct in QUESTIONS:
            Question.objects.create(
                text=text, option_a=a, option_b=b, option_c=c, option_d=d,
                correct_option=correct,
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(QUESTIONS)} questions."))

# exam/models/tec_exam_progress.py

from django.conf import settings
from django.db import models
from django.utils import timezone

from .exam_category import ExamCategory
from .question import MainExamQuestion, Question
from .user_registration import UserRegistration


class TecExamProgress(models.Model):
    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Locked", "Locked"),
        ("Failed", "Failed"),
        ("Passed", "Passed"),
    ]

    user = models.ForeignKey(
        UserRegistration, on_delete=models.CASCADE, related_name="exam_progress"
    )
    exam_category = models.ForeignKey(
        ExamCategory, on_delete=models.CASCADE, related_name="exam_progress"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Open")
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.name} - {self.exam_category.name} - {self.status}"

    def update_progress(self, correct_count):
        """
        Update the progress based on the number of correct answers.
        """
        self.correct_answers = correct_count
        self.total_questions = Question.objects.filter(
            exam_category=self.exam_category
        ).count()

        # Determine status
        if correct_count / self.total_questions >= 0.7:  # Example: 70% required to pass
            self.status = "Passed"
        else:
            self.status = "Failed"

        self.completed_at = models.DateTimeField(auto_now=True)
        self.save()


class MainExamProgress(models.Model):
    STATUS_CHOICES = [
        ("Not Attempted", "Not Attempted"),
        ("Passed", "Passed"),
        ("Failed Attempt 1", "Failed Attempt 1"),
        ("Failed Attempt 2", "Failed Attempt 2"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="main_exam_progress",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Not Attempted"
    )
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    attempt_number = models.IntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - Attempt {self.attempt_number} - {self.status}"

    def update_progress(self, correct_count, attempt_number):
        """
        Update the progress based on the number of correct answers and attempt number.
        """
        self.correct_answers = correct_count
        self.total_questions = MainExamQuestion.objects.count()

        # Determine status based on correct answers and attempt number
        score = correct_count / self.total_questions if self.total_questions else 0
        if score >= 0.7:  # Example: 70% required to pass
            self.status = "Passed"
        elif attempt_number == 1:
            self.status = "Failed Attempt 1"
        elif attempt_number == 2:
            self.status = "Failed Attempt 2"
        else:
            self.status = "Failed Attempt 2"  # Handle additional attempts

        self.completed_at = timezone.now()
        self.save()

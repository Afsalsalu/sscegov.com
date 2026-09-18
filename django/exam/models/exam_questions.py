# exam/models/exam_questions.py

from django.db import models

from .exam_category import ExamCategory


class ExamQuestion(models.Model):
    exam_category = models.ForeignKey(
        ExamCategory, on_delete=models.CASCADE, related_name="exam_questions"
    )
    question_text = models.CharField(max_length=510)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text


class MainExamQuestion(models.Model):
    question_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure question_text is valid UTF-8
        try:
            self.question_text.encode('utf-8')
        except UnicodeEncodeError:
            raise ValueError("Only UTF-8 characters are allowed!")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.question_text
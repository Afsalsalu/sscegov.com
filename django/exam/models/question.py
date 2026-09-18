# exam/models/question.py
import itertools

from django.db import models
from django.utils.text import slugify

from .exam_category import ExamCategory


class Question(models.Model):
    exam_category = models.ForeignKey(
        ExamCategory, on_delete=models.CASCADE, related_name="questions"
    )
    question = models.CharField(max_length=510)
    slug = models.SlugField(unique=True, max_length=255, blank=True)

    def __str__(self):
        return self.question

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.question)
            slug = base_slug
            for x in itertools.count(1):
                if not Question.objects.filter(slug=slug).exists():
                    break
                slug = f"{base_slug}-{x}"
            self.slug = slug
        super().save(*args, **kwargs)


class MainExamQuestion(models.Model):
    # Assuming fields for MainExamQuestion
    question_text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text

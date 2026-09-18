# exam/models/option.py

from django.core.exceptions import ValidationError
from django.db import models

from .question import MainExamQuestion, Question


class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
        blank=True,
        null=True,
    )
    option = models.CharField(max_length=510, blank=True, null=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.option

    def clean(self):
        if self.is_correct:
            if (
                Option.objects.filter(question=self.question, is_correct=True)
                .exclude(pk=self.pk)
                .exists()
            ):
                raise ValidationError(
                    "Only one option can be marked as correct for a question."
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class MainExamOption(models.Model):
    question = models.ForeignKey(
        MainExamQuestion, on_delete=models.CASCADE, related_name="options"
    )
    option = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def clean(self):
        super().clean()
        if self.is_correct:
            correct_options = MainExamOption.objects.filter(
                question=self.question, is_correct=True
            ).exclude(pk=self.pk)
            if correct_options.exists():
                raise ValidationError(
                    "Only one option can be marked as correct for a question."
                )

    def __str__(self):
        return f"{self.option} ({'Correct' if self.is_correct else 'Incorrect'})"

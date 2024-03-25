from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


class Quiz(models.Model):
    title = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField(default='No description provided')

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    def get_correct_choice(self):
        correct_choice = self.choices.filter(is_correct=True).first()
        return correct_choice.text if correct_choice else None

class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

class Attempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.IntegerField()
    date_attempted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student}'s attempt on {self.quiz}"

    def get_student_choice_for_question(self, question):
        try:
            student_answer = self.student_answers.get(question=question)
            return student_answer.choice  # Return the Choice object
        except StudentAnswer.DoesNotExist:
            return None

    def calculate_percentile(self):
        all_scores = Attempt.objects.filter(quiz=self.quiz).order_by('score')
        higher_scores = all_scores.filter(score__gt=self.score).count()
        percentile = (1 - higher_scores / all_scores.count()) * 100
        return percentile


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name='student_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.attempt.student}'s answer to {self.question.text} is {self.choice.text}"


class QuizWeight(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    weight = models.FloatField(default=1.0)

class StudentGrade(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    grade = models.CharField(max_length=2)
    weighted_score = models.FloatField()

    def __str__(self):
        return f"{self.student}'s grade: {self.grade}, weighted score: {self.weighted_score}"
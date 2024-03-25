from django import template
from quizzes.models import Attempt

register = template.Library()

@register.filter
def get_student_choice(attempt, question):
    choice = attempt.get_student_choice_for_question(question)
    return choice.text if choice else "No Answer"

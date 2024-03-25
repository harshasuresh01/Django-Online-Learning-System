from django.urls import path
from . import views
from .views import create_quiz, quiz_list, all_students
from .views import student_grades


urlpatterns = [
    path('list/', views.quiz_list, name='quiz_list'),
    path('create/', create_quiz, name='create_quiz'),
    path('detail/<str:quiz_title>/', views.quiz_detail, name='quiz_detail'),
    path('all-students/', views.all_students, name='all_students'),
    path('student-detail/<int:student_id>/', views.student_detail, name='student_detail'),
    path('set-quiz-weight/', views.set_quiz_weight, name='set_quiz_weight'),
    path('student-grades/', student_grades, name='student-grades'),


]

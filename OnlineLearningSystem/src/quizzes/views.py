import json

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg

from .models import Quiz, Attempt, Question, Choice, StudentAnswer
from .forms import QuizForm, QuestionForm, ChoiceForm
from account.models import Account
from django.db.models import Max, Min, Avg, F
from .models import QuizWeight, StudentGrade
from django.contrib.auth.decorators import user_passes_test




@login_required
def quiz_list(request):
    search_query = request.GET.get('q', '')
    if search_query:
        quizzes = Quiz.objects.filter(title__icontains=search_query).order_by('title')
    else:
        quizzes = Quiz.objects.all().order_by('title')

    quizzes_with_attempts = []
    student_percentages = {}  # Dictionary to hold percentage scores for each quiz

    for quiz in quizzes:
        # Add weight to each quiz
        quiz_weight = QuizWeight.objects.filter(quiz=quiz).first()
        if quiz_weight:
            quiz.weight = quiz_weight.weight
        else:
            quiz.weight = 0

        attempt = Attempt.objects.filter(quiz=quiz, student=request.user).order_by('-date_attempted').first()
        quizzes_with_attempts.append((quiz, attempt))

        if attempt:
            total_questions = quiz.questions.count()
            if total_questions > 0:
                percentage_score = (attempt.score / total_questions) * 100
                student_percentages[quiz.title] = round(percentage_score, 2)
            else:
                student_percentages[quiz.title] = None
        else:
            student_percentages[quiz.title] = None

    subject_labels = list(student_percentages.keys())
    subject_values = [percent if percent is not None else 0 for percent in student_percentages.values()]

    subject_labels_json = json.dumps(subject_labels)
    subject_values_json = json.dumps(subject_values)

    # Calculate the weighted score for the logged-in student
    if not request.user.is_teacher:
        weighted_score = compute_weighted_score(request.user)
        letter_grade = assign_letter_grade(weighted_score)
    else:
        weighted_score = None
        letter_grade = None


    if request.user.is_teacher:
        letter_grade_labels, letter_grade_counts = compute_letter_grade_distribution()
    else:
        letter_grade_labels, letter_grade_counts = None, None

    return render(request, 'quizzes/quiz_list.html', {
        'quizzes_with_attempts': quizzes_with_attempts,
        'quizzes': quizzes,
        'search_query': search_query,
        'subject_labels': subject_labels_json,
        'subject_values': subject_values_json,
        'weighted_score': weighted_score,
        'letter_grade': letter_grade,
        'letter_grade_labels': json.dumps(letter_grade_labels) if letter_grade_labels is not None else None,
        'letter_grade_counts': json.dumps(letter_grade_counts) if letter_grade_counts is not None else None,
    })






from django.utils import timezone




def get_remaining_attempts(user, quiz):
    attempt_count = Attempt.objects.filter(quiz=quiz, student=user).count()
    return max(3 - attempt_count, 0)



@login_required
def quiz_detail(request, quiz_title):
    quiz = get_object_or_404(Quiz, title=quiz_title)
    user_account = Account.objects.get(email=request.user.email)
    remaining_attempts = get_remaining_attempts(request.user, quiz)

    if user_account.is_teacher:
        student_attempts = Attempt.objects.filter(quiz=quiz).select_related('student')

        # Sorting logic
        sort_by = request.GET.get('sort', 'score')  # Default sort by score
        order = request.GET.get('order', 'asc')
        if order == 'desc':
            sort_by = '-' + sort_by
        student_attempts = student_attempts.order_by(sort_by)

        # Calculate additional details for each attempt
        for attempt in student_attempts:
            attempt.percentile = calculate_percentile(attempt, quiz)

        highest_score = student_attempts.aggregate(Max('score'))['score__max']
        lowest_score = student_attempts.aggregate(Min('score'))['score__min']
        total_questions = quiz.questions.count()
        if total_questions > 0:
            average_score = student_attempts.aggregate(Avg('score'))['score__avg']
            average_percentage_score = (average_score / total_questions) * 100
        else:
            average_percentage_score = None

        # Calculate letter grade distribution for the pie chart
        grade_distribution = {}
        for attempt in student_attempts:
            letter_grade = assign_letter_grade((attempt.score / total_questions) * 100)
            grade_distribution[letter_grade] = grade_distribution.get(letter_grade, 0) + 1

        grade_labels = list(grade_distribution.keys())
        grade_counts = list(grade_distribution.values())

        context = {
            'quiz': quiz,
            'student_attempts': student_attempts,
            'highest_score': highest_score,
            'lowest_score': lowest_score,
            'average_score': average_percentage_score,  # Updated line
            'letter_grade_labels': json.dumps(grade_labels),
            'letter_grade_counts': json.dumps(grade_counts)
        }
        return render(request, 'quizzes/quiz_detail_teacher.html', context)

    else:
        # Handling student's quiz attempt
        attempts = Attempt.objects.filter(quiz=quiz, student=request.user).order_by('-date_attempted')
        remaining_attempts = 3 - attempts.count()
        latest_attempt = attempts.first()

        # Calculate percentile for the latest attempt
        latest_attempt_percentile = None
        if latest_attempt:
            latest_attempt_percentile = calculate_percentile(latest_attempt, quiz)

        if request.method == 'POST' and remaining_attempts > 0:
            # Handling quiz submission
            if 'retake_quiz' in request.POST:
                latest_attempt = None
                remaining_attempts -= 1
            else:
                score = 0
                for question in quiz.questions.all():
                    selected_choice_id = request.POST.get(f'question_{question.id}')
                    if selected_choice_id:
                        selected_choice = Choice.objects.get(id=selected_choice_id)
                        if selected_choice.is_correct:
                            score += 1
                new_attempt = Attempt.objects.create(quiz=quiz, student=request.user, score=score, date_attempted=timezone.now())
                latest_attempt = new_attempt
                latest_attempt_percentile = calculate_percentile(latest_attempt, quiz)
                remaining_attempts = 3 - attempts.count() - 1

        context = {
            'quiz': quiz,
            'latest_attempt': latest_attempt,
            'latest_attempt_percentile': latest_attempt_percentile,
            'remaining_attempts': remaining_attempts,
            'max_attempts': 3
        }
        return render(request, 'quizzes/quiz_detail_student.html', context)










@login_required
def create_quiz(request):
    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)
        if quiz_form.is_valid():
            quiz = quiz_form.save(commit=False)
            quiz.created_by = request.user
            quiz.save()

            # Process each question
            for i in range(0, 100):  # Assuming a maximum of 100 questions for safety
                question_text = request.POST.get(f'questions-{i}-text')
                if not question_text:
                    break  # Break if no more questions are found

                question = Question.objects.create(quiz=quiz, text=question_text)

                # Process each choice for the question
                for j in range(4):  # Assuming 4 choices per question
                    choice_text = request.POST.get(f'questions-{i}-choice-{j}')
                    correct_choice = request.POST.get(f'questions-{i}-correct')
                    if choice_text:
                        is_correct = False
                        if correct_choice.isdigit():
                            is_correct = (j + 1) == int(correct_choice)
                        Choice.objects.create(
                            question=question,
                            text=choice_text,
                            is_correct=is_correct
                        )

            return redirect('quizzes:quiz_list')
        else:
            return render(request, 'quizzes/create_quiz.html', {'quiz_form': quiz_form})
    else:
        quiz_form = QuizForm()

    return render(request, 'quizzes/create_quiz.html', {'quiz_form': quiz_form})








def get_subject_from_title(title):
    return title.split()[0]  # Assuming the first word is the subject









@login_required
def all_students(request):
    if not request.user.is_teacher:
        return redirect('quizzes:quiz_list')

    # Get all student accounts
    students = Account.objects.filter(is_teacher=False)
    return render(request, 'quizzes/all_students.html', {'students': students})






@login_required
def student_detail(request, student_id):
    if not request.user.is_teacher:
        return redirect('quizzes:quiz_list')

    student = get_object_or_404(Account, id=student_id)

    # Fetch all attempts made by the student
    attempts = Attempt.objects.filter(student=student).select_related('quiz')

    # Annotate each attempt with the total number of questions in the quiz
    attempts = attempts.annotate(total_questions=Count('quiz__questions'))

    # Calculate percentage scores
    attempts = attempts.annotate(
        percentage_score=100 * F('score') / F('total_questions')
    )

    # Sorting logic
    sort_by = request.GET.get('sort', 'percentage_score')  # Default sort by percentage score
    order = request.GET.get('order', 'asc')

    if order == 'desc':
        sort_by = '-' + sort_by

    attempts = attempts.order_by(sort_by)

    # Calculate aggregate values
    aggregate_values = attempts.aggregate(
        highest_score=Max('percentage_score'),
        lowest_score=Min('percentage_score'),
        average_score=Avg('percentage_score')
    )

    # Calculate weighted score and letter grade for the student
    weighted_score = compute_weighted_score(student)
    letter_grade = assign_letter_grade(weighted_score)

    return render(request, 'quizzes/student_detail.html', {
        'student': student,
        'attempts': attempts,
        'highest_score': aggregate_values['highest_score'],
        'lowest_score': aggregate_values['lowest_score'],
        'average_score': aggregate_values['average_score'],
        'weighted_score': weighted_score,
        'letter_grade': letter_grade
    })






def compute_weighted_score(student):
    attempts = Attempt.objects.filter(student=student)
    total_weighted_score = 0
    total_weight = 0

    for attempt in attempts:
        quiz_weight = QuizWeight.objects.get(quiz=attempt.quiz).weight
        total_questions = attempt.quiz.questions.count()
        if total_questions > 0:
            normalized_score = attempt.score / total_questions  # Normalize the score
            total_weighted_score += normalized_score * quiz_weight
        total_weight += quiz_weight

    if total_weight > 0:
        weighted_score_percentage = (total_weighted_score / total_weight) * 100
        return round(weighted_score_percentage, 2)  # Round to 2 decimal places
    else:
        return 0



def assign_letter_grade(weighted_score):
    if weighted_score >= 90:
        return 'A'
    elif weighted_score >= 80:
        return 'B'
    elif weighted_score >= 70:
        return 'C'
    elif weighted_score >= 60:
        return 'D'
    elif weighted_score < 60:
        return 'F'




def update_student_grades():
    for student in User.objects.filter(is_student=True):
        weighted_score = compute_weighted_score(student)
        grade = assign_letter_grade(weighted_score)
        StudentGrade.objects.update_or_create(
            student=student,
            defaults={'grade': grade, 'weighted_score': weighted_score}
        )







@user_passes_test(lambda u: u.is_teacher)
def set_quiz_weight(request):
    if request.method == 'POST' and request.user.is_teacher:
        # Get the quiz ID and weight from the POST request
        quiz_id = request.POST.get('quiz_id')
        weight = request.POST.get('weight')

        # Ensure the weight is a valid number
        try:
            weight = float(weight)
        except ValueError:
            # Handle the error if weight is not a valid number
            # Redirect to an error page or show a message
            return redirect('error_view_name')  # Replace with your error view

        # Get the quiz object
        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Update or create the QuizWeight entry
        QuizWeight.objects.update_or_create(
            quiz=quiz,
            defaults={'weight': weight}
        )

        # Redirect to a success page or the quiz list
        return redirect('quizzes:quiz_list')  # Replace 'quizzes:quiz_list' with your desired redirect view
    else:
        # Redirect to home or an error page if the request is not POST or the user is not a teacher
        return redirect('home_view_name')  # Replace with your home or error view





@login_required
def student_grades(request):
    if not request.user.is_teacher:
        return redirect('some_other_view')

    students = Account.objects.filter(is_teacher=False)
    for student in students:
        student.weighted_score = compute_weighted_score(student)
        student.letter_grade = assign_letter_grade(student.weighted_score)

    return render(request, 'student_grades.html', {'students': students})




def compute_letter_grade_distribution():
    grades = StudentGrade.objects.values('grade').annotate(count=Count('grade'))
    grade_labels = [grade['grade'] for grade in grades]
    grade_counts = [grade['count'] for grade in grades]
    return grade_labels, grade_counts









def calculate_percentile(attempt, quiz):
    all_attempts = Attempt.objects.filter(quiz=quiz).exclude(id=attempt.id)
    attempts_count = all_attempts.count()

    if attempts_count > 0:
        higher = sum(1 for other_attempt in all_attempts if other_attempt.score > attempt.score)
        equal = sum(1 for other_attempt in all_attempts if other_attempt.score == attempt.score)
        percentile_rank = (higher + 0.5 * equal) / attempts_count * 100
        return round(percentile_rank, 2)
    else:
        # Indicate that percentile calculation is not applicable
        return None  # or return 'N/A' or any other appropriate value










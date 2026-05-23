from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import models
from .models import LearningActivity
import re
import json
import io
import sys
import ast

from .models import Level, Topic, Task, Submission, ConceptProgress


# --------from groq import Groq
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)
#-------- AUTH APIs ----------------

@csrf_exempt
def register(request):
    if request.method == "POST":
        data = json.loads(request.body)

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return JsonResponse({"error": "Username & password required"}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "User already exists"}, status=400)

        User.objects.create_user(username=username, password=password)

        return JsonResponse({"message": "User registered successfully"})

    return JsonResponse({"error": "POST only"}, status=405)


@csrf_exempt
def login_api(request):
    if request.method == "POST":

        data = json.loads(request.body)

        user = authenticate(
            username=data.get("username"),
            password=data.get("password")
        )

        if user:
            django_login(request, user)

            return JsonResponse({
                "message": "Login success",
                "username": user.username
            })

        return JsonResponse({"error": "Invalid credentials"}, status=400)

    return JsonResponse({"error": "POST only"}, status=405)


@csrf_exempt
def logout_api(request):
    if request.method == "POST":
        django_logout(request)
        return JsonResponse({"message": "Logged out"})

    return JsonResponse({"error": "POST only"}, status=405)


def session_check(request):
    if request.user.is_authenticated:
        return JsonResponse({
            "authenticated": True,
            "username": request.user.username
        })

    return JsonResponse({"authenticated": False})


# ---------------- PAGE VIEWS ----------------

def login_page(request):
    return render(request, "concept2code/login.html")


def register_page(request):
    return render(request, "concept2code/register.html")


@login_required(login_url="/login/")
def dashboard(request):

    user_submissions = Submission.objects.filter(user=request.user)

    total_submissions = user_submissions.count()

    solved_tasks = Submission.objects.filter(
        user=request.user
    ).values("task").distinct().count()

    average_score = (
        user_submissions.aggregate(models.Avg("score"))["score__avg"]
        if total_submissions > 0 else 0
    )

    highest_score = (
        user_submissions.aggregate(models.Max("score"))["score__max"]
        if total_submissions > 0 else 0
    )

    leaderboard = (
        Submission.objects
        .values("user__username")
        .annotate(total_score=models.Sum("score"))
        .order_by("-total_score")[:5]
    )

    concepts = ["loop", "stack", "hashmap", "recursion"]

    progress = []

    for concept in concepts:
        unlocked = ConceptProgress.objects.filter(
            user=request.user,
            concept=concept,
            unlocked=True
        ).exists()

        progress.append({
            "name": concept,
            "unlocked": unlocked
        })

    activities = LearningActivity.objects.filter(
        user=request.user
    ).order_by("-created_at")[:10]

    recommended_tasks = []

    for concept in concepts:

        progress_obj = ConceptProgress.objects.filter(
            user=request.user,
            concept=concept
        ).first()

        percent = progress_obj.progress if progress_obj else 0

        if percent < 50:

            tasks = Task.objects.filter(
                expected_concept=concept
            )[:3]

            for t in tasks:
                recommended_tasks.append(t)

    return render(request, "concept2code/dashboard.html", {
        "total_submissions": total_submissions,
        "solved_tasks": solved_tasks,
        "average_score": round(average_score, 2) if average_score else 0,
        "highest_score": highest_score,
        "leaderboard": leaderboard,
        "progress": progress,
        "activities": activities,
        "recommended_tasks": recommended_tasks
    })


@login_required(login_url="/login/")
def level_list(request):

    levels = Level.objects.all()

    return render(request, "concept2code/levels.html", {
        "levels": levels
    })


@login_required(login_url="/login/")
def topic_list(request, level_id):

    level = get_object_or_404(Level, id=level_id)

    topics = Topic.objects.filter(level=level)

    return render(request, "concept2code/topics.html", {
        "level": level,
        "topics": topics
    })


@login_required(login_url="/login/")
def task_list(request, topic_id):

    topic = get_object_or_404(Topic, id=topic_id)

    paginator = Paginator(
        Task.objects.filter(topic=topic),
        5
    )

    page_number = request.GET.get("page")

    tasks = paginator.get_page(page_number)

    return render(request, "concept2code/tasks.html", {
        "topic": topic,
        "tasks": tasks
    })


@login_required(login_url="/login/")
def task_detail(request, task_id):

    task = get_object_or_404(Task, id=task_id)

    submissions = Submission.objects.filter(
        user=request.user,
        task=task
    ).order_by("-created_at")

    best_submission = Submission.objects.filter(
        user=request.user,
        task=task
    ).order_by("-score").first()

    return render(request, "concept2code/task_detail.html", {
        "task": task,
        "submissions": submissions,
        "best_score": best_submission.score if best_submission else None
    })


# ---------------- SUBMISSION API ----------------

@csrf_exempt
@login_required(login_url="/login/")
def submit_code(request):

    if request.method == "POST":

        data = json.loads(request.body)

        code = data.get("code")

        if not code or not code.strip():
            return JsonResponse({"error": "Code cannot be empty"}, status=400)

        task = get_object_or_404(Task, id=data.get("task_id"))

        previous_attempts = Submission.objects.filter(
            user=request.user,
            task=task
        ).count()

        base_score = 100 * task.topic.level.score_multiplier

        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()

        try:
            exec(code)
            output = buffer.getvalue()

        except Exception as e:
            output = str(e)
            base_score -= 20

        sys.stdout = old_stdout

        tree = ast.parse(code)

        max_depth = 0

        def get_loop_depth(node, depth=0):

            nonlocal max_depth

            if isinstance(node, (ast.For, ast.While)):
                depth += 1
                max_depth = max(max_depth, depth)

            for child in ast.iter_child_nodes(node):
                get_loop_depth(child, depth)

        get_loop_depth(tree)

        complexity = "O(n)" if max_depth else "O(1)"

        analysis = {
            "estimated_complexity": complexity,
            "detected_concepts": ["loop"] if max_depth else [],
            "structural_hints": ["Your solution uses loops."],
            "behavioral_hints": ["Nested loops increase time complexity."],
            "optimization_hints": ["Try reducing nested loops."],
            "ai_explanation": ["Your code was analyzed successfully."],
            "complexity_explanation": ["Basic complexity analysis."],
            "optimization_suggestions": ["Your algorithm structure looks efficient."]
        }

        submission = Submission.objects.create(
            user=request.user,
            task=task,
            code=code,
            score=base_score
        )

        LearningActivity.objects.create(
            user=request.user,
            message=f"Solved task: {task.title}"
        )

        return JsonResponse({
            "message": "Code submitted!",
            "output": output,
            "analysis": analysis,
            "score": base_score,
            "auto_hint": "Think about what data structure fits this problem.",
            "submission_id": submission.id
        })

    return JsonResponse({"error": "POST only"}, status=405)




@csrf_exempt
@login_required(login_url="/login/")
def generate_code(request):

    if request.method == "POST":

        data = json.loads(request.body)
        text = data.get("text", "")

        try:

            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Python code generator. Convert English instructions into Python code only."
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                temperature=0.2
            )

            code = completion.choices[0].message.content

        except Exception as e:
            code = f"# Error generating code: {str(e)}"

        return JsonResponse({
            "generated_code": code
        })

    return JsonResponse({"error": "POST only"}, status=405)
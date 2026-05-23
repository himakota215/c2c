from django.db import models
from django.contrib.auth.models import User


class Level(models.Model):

    name = models.CharField(max_length=50)

    score_multiplier = models.IntegerField(default=1)

    def __str__(self):
        return self.name


class Topic(models.Model):
    name = models.CharField(max_length=100)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.level.name} - {self.name}"


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)

    expected_concept = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.title


class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)

    code = models.TextField()

    score = models.IntegerField(default=100)

    hints_used = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.task.title} - {self.score}"


# NEW MODEL
class ConceptProgress(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    concept = models.CharField(max_length=100)

    unlocked = models.BooleanField(default=False)

    unlocked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.concept}"
class LearningActivity(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.message}"
class ConceptProgress(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    concept = models.CharField(max_length=50)

    unlocked = models.BooleanField(default=False)

    progress = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} - {self.concept}"
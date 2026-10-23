"""
MUJVERSE — Reviews URL Patterns
"""

from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("my-reviews/", views.student_reviews_view, name="my_reviews"),
]

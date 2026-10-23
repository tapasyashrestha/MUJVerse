"""
MUJVERSE — Reviews URL Patterns
"""

from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("my-reviews/", views.student_reviews_view, name="my_reviews"),
    path("events/<int:event_id>/create/", views.create_review_view, name="create_review"),
    path("events/<int:pk>/reviews/", views.organizer_event_reviews_view, name="organizer_reviews"),
]

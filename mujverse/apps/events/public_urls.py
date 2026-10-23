"""
MUJVERSE — Public URL Patterns
"""

from django.urls import path
from . import views

app_name = "public"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("events/", views.explore_view, name="explore"),
    path("events/<slug:slug>/", views.event_detail_view, name="event_detail"),
    path("categories/", views.categories_view, name="categories"),
    path("about/", views.about_view, name="about"),
    path("help/", views.help_view, name="help"),
]

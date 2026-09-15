from django.urls import path

from . import views

urlpatterns = [
    path("persons/search/", views.PersonSearchView.as_view(), name="persons-search"),
]

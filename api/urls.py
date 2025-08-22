from django.urls import path

from api.views import (
    EditTaskDetailView,
    EditTaskListView,
    EditView,
    ResultView,
    SectionHeadingsView,
)

app_name = 'api'

urlpatterns = [
    path("edit/<str:editing_mode>", EditView.as_view(), name="edit"),
    path("results/<str:task_id>", ResultView.as_view(), name="results"),
    path("section-headings", SectionHeadingsView.as_view(), name="section-headings"),
    path("tasks/", EditTaskListView.as_view(), name="task-list"),
    path("tasks/<str:task_id>/", EditTaskDetailView.as_view(), name="task-detail"),
]
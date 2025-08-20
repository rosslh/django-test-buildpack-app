from django.urls import path
from .views import HealthCheckView, EditView, ResultView, SectionHeadingsView

app_name = 'api'

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health'),
    path('edit/<str:editing_mode>/', EditView.as_view(), name='edit'),
    path('results/<str:task_id>/', ResultView.as_view(), name='results'),
    path('section-headings/', SectionHeadingsView.as_view(), name='section-headings'),
]
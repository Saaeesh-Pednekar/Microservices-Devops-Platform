from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health_check, name='health-check'),
    path('info/', views.app_info, name='app-info'),
    path('tasks/', views.task_list, name='task-list'),
    path('tasks/add/', views.task_add, name='task-add'),
    path('tasks/delete/<int:task_id>/', views.task_delete, name='task-delete'),
    path('tasks/toggle/<int:task_id>/', views.task_toggle, name='task-toggle'),
]

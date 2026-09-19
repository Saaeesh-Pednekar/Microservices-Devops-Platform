import os
import json
import platform
import time
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

APP_VERSION = os.environ.get('APP_VERSION', '1.0.0')
ENVIRONMENT = os.environ.get('APP_ENVIRONMENT', 'development')
START_TIME = time.time()

# In-memory task store (no database needed for this demo)
_tasks = [
    # {'id': 1, 'title': 'Learn Kubernetes fundamentals', 'completed': True},
    # {'id': 2, 'title': 'Set up CI/CD pipeline with Jenkins', 'completed': False},
    # {'id': 3, 'title': 'Deploy application to AWS EKS', 'completed': False},
]
_next_id = 1


def health_check(request):
    """Kubernetes readiness/liveness probe endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


def app_info(request):
    """Returns application metadata — version, environment, host, uptime."""
    uptime_seconds = int(time.time() - START_TIME)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return JsonResponse({
        'app_name': 'DevOps Platform',
        'version': APP_VERSION,
        'environment': ENVIRONMENT,
        'hostname': platform.node(),
        'python_version': platform.python_version(),
        'uptime': f'{hours}h {minutes}m {seconds}s',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })


@csrf_exempt
@require_http_methods(['GET'])
def task_list(request):
    """List all tasks."""
    return JsonResponse({'tasks': _tasks, 'count': len(_tasks)})


@csrf_exempt
@require_http_methods(['POST'])
def task_add(request):
    """Add a new task."""
    global _next_id
    try:
        body = json.loads(request.body)
        title = body.get('title', '').strip()
        if not title:
            return JsonResponse({'error': 'Title is required'}, status=400)

        task = {'id': _next_id, 'title': title, 'completed': False}
        _tasks.append(task)
        _next_id += 1
        return JsonResponse({'task': task, 'message': 'Task created'}, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(['DELETE'])
def task_delete(request, task_id):
    """Delete a task by ID."""
    global _tasks
    original_len = len(_tasks)
    _tasks = [t for t in _tasks if t['id'] != task_id]
    if len(_tasks) == original_len:
        return JsonResponse({'error': 'Task not found'}, status=404)
    return JsonResponse({'message': 'Task deleted'})


@csrf_exempt
@require_http_methods(['PATCH'])
def task_toggle(request, task_id):
    """Toggle a task's completed status."""
    for task in _tasks:
        if task['id'] == task_id:
            task['completed'] = not task['completed']
            return JsonResponse({'task': task, 'message': 'Task updated'})
    return JsonResponse({'error': 'Task not found'}, status=404)

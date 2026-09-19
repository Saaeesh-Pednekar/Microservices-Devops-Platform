from django.test import TestCase, Client
import json


class HealthCheckTest(TestCase):
    def test_health_returns_200(self):
        client = Client()
        response = client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'healthy')


class AppInfoTest(TestCase):
    def test_info_returns_version(self):
        client = Client()
        response = client.get('/api/info/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('version', data)
        self.assertIn('environment', data)
        self.assertIn('hostname', data)


class TaskAPITest(TestCase):
    def test_list_tasks(self):
        client = Client()
        response = client.get('/api/tasks/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('tasks', data)
        self.assertEqual(data['count'], 0)

    def test_add_task(self):
        client = Client()
        response = client.post(
            '/api/tasks/add/',
            data=json.dumps({'title': 'Test task'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['task']['title'], 'Test task')

    def test_add_task_empty_title(self):
        client = Client()
        response = client.post(
            '/api/tasks/add/',
            data=json.dumps({'title': ''}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_toggle_task(self):
        client = Client()
        response = client.patch('/api/tasks/toggle/1/')
        self.assertEqual(response.status_code, 200)

    def test_delete_task_not_found(self):
        client = Client()
        response = client.delete('/api/tasks/delete/9999/')
        self.assertEqual(response.status_code, 404)

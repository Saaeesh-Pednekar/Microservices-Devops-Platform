import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = '/api';

export default function App() {
  const [info, setInfo] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [infoRes, tasksRes] = await Promise.all([
        fetch(`${API_BASE}/info/`),
        fetch(`${API_BASE}/tasks/`),
      ]);

      if (!infoRes.ok || !tasksRes.ok) throw new Error('API request failed');

      const infoData = await infoRes.json();
      const tasksData = await tasksRes.json();

      setInfo(infoData);
      setTasks(tasksData.tasks);
      setError(null);
    } catch (err) {
      setError('Unable to connect to the backend API. Is the server running?');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const addTask = async (e) => {
    e.preventDefault();
    if (!newTask.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/tasks/add/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTask.trim() }),
      });
      if (!res.ok) throw new Error('Failed to add task');
      const data = await res.json();
      setTasks((prev) => [...prev, data.task]);
      setNewTask('');
    } catch (err) {
      setError('Failed to add task');
    }
  };

  const toggleTask = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/toggle/${id}/`, {
        method: 'PATCH',
      });
      if (!res.ok) throw new Error('Failed to toggle task');
      const data = await res.json();
      setTasks((prev) =>
        prev.map((t) => (t.id === id ? data.task : t))
      );
    } catch (err) {
      setError('Failed to update task');
    }
  };

  const deleteTask = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/tasks/delete/${id}/`, {
        method: 'DELETE',
      });
      if (!res.ok) throw new Error('Failed to delete task');
      setTasks((prev) => prev.filter((t) => t.id !== id));
    } catch (err) {
      setError('Failed to delete task');
    }
  };

  if (loading) return <div className="loading">Connecting to backend...</div>;

  return (
    <div className="app">
      <header className="header">
        <h1>⚙️ DevOps Platform</h1>
        <p>CI/CD Pipeline Demo &mdash; Django + React on Kubernetes</p>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {info && (
        <div className="info-grid">
          <div className="info-card">
            <div className="label">Version</div>
            <div className="value">{info.version}</div>
          </div>
          <div className="info-card">
            <div className="label">Environment</div>
            <div className="value">{info.environment}</div>
          </div>
          <div className="info-card">
            <div className="label">Status</div>
            <div className="value healthy">
              ● Online
            </div>
          </div>
          <div className="info-card">
            <div className="label">Hostname</div>
            <div className="value">{info.hostname}</div>
          </div>
          <div className="info-card">
            <div className="label">Uptime</div>
            <div className="value">{info.uptime}</div>
          </div>
          <div className="info-card">
            <div className="label">Python</div>
            <div className="value">{info.python_version}</div>
          </div>
        </div>
      )}

      <h2 className="section-title">📋 Task Manager</h2>

      <form className="task-input-row" onSubmit={addTask}>
        <input
          type="text"
          placeholder="Add a new task..."
          value={newTask}
          onChange={(e) => setNewTask(e.target.value)}
        />
        <button type="submit">Add Task</button>
      </form>

      {tasks.length === 0 ? (
        <div className="empty-state">No tasks yet. Add one above!</div>
      ) : (
        <ul className="task-list">
          {tasks.map((task) => (
            <li key={task.id} className="task-item">
              <input
                type="checkbox"
                checked={task.completed}
                onChange={() => toggleTask(task.id)}
              />
              <span className={`title ${task.completed ? 'done' : ''}`}>
                {task.title}
              </span>
              <button
                className="delete-btn"
                onClick={() => deleteTask(task.id)}
                title="Delete task"
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <footer className="footer">
        Built with Django &amp; React &bull; Deployed via Jenkins CI/CD to AWS EKS
      </footer>
    </div>
  );
}

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_auth_endpoints_exist():
    # Missing required fields must be a validation response, not a server error.
    register = client.post('/api/auth/register', json={})
    login = client.post('/api/auth/login', json={})
    assert register.status_code == 422
    assert login.status_code == 422


def test_protected_endpoints_require_auth():
    for path in [
        '/api/auth/me', '/api/customers', '/api/products', '/api/invoices',
        '/api/quotes', '/api/expenses', '/api/settings', '/api/dashboard/summary',
    ]:
        response = client.get(path)
        assert response.status_code == 401, f'{path} returned {response.status_code}'

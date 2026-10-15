from app.security.passwords import hash_password, verify_password


def test_password_hash_is_salted_and_verifiable():
    a = hash_password('Password123!')
    b = hash_password('Password123!')
    assert a != b
    assert verify_password('Password123!', a)
    assert not verify_password('wrong', a)


def test_protected_route_requires_auth(client):
    # Clear cookies from any preceding session-scoped interaction.
    client.cookies.clear()
    response = client.get('/api/dashboard')
    assert response.status_code == 401


def test_register_login_and_me(client):
    client.cookies.clear()
    response = client.post('/api/auth/register', json={'full_name':'Ahmed Tester','email':'ahmed.test@example.com','password':'Password123!'})
    assert response.status_code == 201
    me = client.get('/api/me')
    assert me.status_code == 200
    assert me.json()['email'] == 'ahmed.test@example.com'
    client.post('/api/auth/logout')
    assert client.get('/api/me').status_code == 401
    login = client.post('/api/auth/login', json={'email':'ahmed.test@example.com','password':'Password123!'})
    assert login.status_code == 200


def test_refresh_session(client):
    payload = {"full_name": "Refresh User", "email": "refresh@example.com", "password": "StrongPass123!"}
    register = client.post("/api/auth/register", json=payload)
    assert register.status_code == 201
    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["user"]["email"] == payload["email"]

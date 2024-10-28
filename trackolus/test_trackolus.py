import pytest
from app import create_app, errdb, ErrorLog
from unittest.mock import patch

@pytest.fixture
def app():
    app = create_app(testing=True)
    app.secret_key = 'EsAlItErAsE'
    app.config['TESTING'] = True

    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def test_login_page(client):
    response = client.get('/login')

    assert response.status_code == 200
    assert b"Trackolus" in response.data


def test_error_logging(client):
    response = client.get('/testing_false_route')
    
    assert response.status_code == 500

    with client.application.app_context():
        error_logs = errdb.session.query(ErrorLog).all()
        assert len(error_logs) > 0
        last_log = error_logs[-1]
        assert last_log.error_message is not None
        assert last_log.error_trace is not None
        assert last_log.ip_address is not None
        assert last_log.endpoint == '/testing_false_route'


def test_login_authentication(client):
    with patch('app.get_locale', return_value='en'):
        response = client.post('/login', data={
            'identification': '0000',
            'password': '0000'
        }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'error-face' not in response.data

    with client.session_transaction() as session:
        assert session['user_id'] == 3
        assert session['role'] == 'admin'
        assert session['name'] == 'Testing user'
        assert session['inventory_order'] == False
        assert session['language'] == 'en'


def test_login_validation(client):
    response = client.post('/login', data={
        "password": "0000"
    })
    assert response.status_code == 400
    
    response = client.post('/login', data={
        "identification": "0000"
    })
    assert response.status_code == 400
    
    response = client.post('/login', data={
        "identification": "wrong_user",
        "password": "wrong_password"
    })
    assert response.status_code == 401


def test_logout(client):
    with client.session_transaction() as session:
        session['user_id'] = 3

    response = client.get('/logout', follow_redirects=False)

    assert response.status_code == 302
    assert b'error-face' not in response.data
    assert response.headers["Location"] == "/login"
    with client.session_transaction() as session:
        assert len(session) == 0


def test_inventory(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'admin'
        
    response = client.get('/inventory')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'id="warehouses-' in response.data
    assert b'more-button' in response.data

    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'observer'
        
    response = client.get('/inventory')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'id="warehouses-' in response.data
    assert b'more-button' not in response.data


def test_dashboard_page(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['language'] = 'en'
    
    response = client.get('/dashboard')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'inventory_graph1' in response.data
    assert b'inventory_graph2' in response.data
    assert b'inventory_graph3' in response.data


def test_purchase_order(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'admin'

    response = client.get('/purchase_order')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'purchase-cart' in response.data


def test_inbound(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'admin'
        
    response = client.get('/inbound')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'<b>Supplier:</b>' in response.data
    assert b'id="add-button"' in response.data

    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'observer'
        
    response = client.get('/inbound')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'<b>Supplier:</b>' in response.data
    assert b'id="add-button"' not in response.data


def test_outound(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        
    response = client.get('/outbound')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'<b>Customer:</b>' in response.data


@pytest.mark.parametrize("datatype", [
    'Customers', 
    'Suppliers', 
    'Products', 
    'Inbound', 
    'Outbound', 
    'Users'
])
def test_reports(client, datatype):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'admin'
        session['language'] = 'en'
        
    response = client.post('/reports', data={
        'datatype': datatype 
    })
    snippet = f'data_title">{datatype}'
    byte_snippet = snippet.encode('utf-8')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert byte_snippet in response.data


def test_user_filter(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'admin'
        session['language'] = 'en'

    response = client.get('/user_filter')

    assert response.status_code == 200
    assert b'user-select' in response.data


def test_activity(client):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'admin'
        session['language'] = 'en'

    response = client.post('/reports', data={
        'datatype': 'Activity',
        'user-select': 'Testing user' 
    })
    print(response.data)
    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert b'data_title">Activity' in response.data


@pytest.mark.parametrize("datatype", ['Users', 'Activity'])
def restricted_report(client, datatype):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'observer'
        session['language'] = 'en'

    response = client.post('/reports', data={
        'datatype': datatype,
    })

    assert response.status_code == 403
    assert b'error-face' in response.data
    assert b'Forbbiden' in response.data

@pytest.mark.parametrize("endpoint,snippet", [
    ('help', 'WMS'),
    ('calendar', 'dayGridMonth'),
    ('settings', 'change-password')
])
def test_others(client, endpoint, snippet):
    with client.session_transaction() as session:
        session['user_id'] = 3
        session['role'] = 'observer'
        session['language'] = 'en'
    
    response = client.get(f'/{endpoint}')
    byte_snippet = snippet.encode('utf-8')

    assert response.status_code == 200
    assert b'error-face' not in response.data
    assert byte_snippet in response.data

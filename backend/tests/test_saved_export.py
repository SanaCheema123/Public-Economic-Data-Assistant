
def _login(client, account):
    client.post('/api/auth/login', json={'email': account['email'], 'password': account['password']})


def test_save_and_csv_export(client, account):
    _login(client, account)
    chat = client.post('/api/chat', json={'question':'Show GDP growth for the last 5 years.','language':'en'})
    assert chat.status_code == 200
    result = chat.json()
    saved = client.post('/api/saved', json={
        'query_result_id': result['result_id'], 'item_type':'answer', 'title':'GDP research',
        'description': result['answer'], 'payload': {'verification_status': 'verified'}
    })
    assert saved.status_code == 201
    listing = client.get('/api/saved?item_type=answer')
    assert listing.status_code == 200
    assert any(x['title']=='GDP research' for x in listing.json()['items'])
    export = client.post('/api/export/csv', json={'query_result_id': result['result_id'], 'language':'en'})
    assert export.status_code == 200
    assert export.headers['content-type'].startswith('text/csv')
    assert b'indicator' in export.content


def test_pdf_export(client, account):
    _login(client, account)
    chat = client.post('/api/chat', json={'question':'What is inflation in 2023?','language':'en'}).json()
    response = client.post('/api/export/pdf', json={'query_result_id':chat['result_id'],'language':'en'})
    assert response.status_code == 200
    assert response.content.startswith(b'%PDF')

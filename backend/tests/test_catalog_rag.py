from app.database.session import SessionLocal
from app.services.rag.retrieval import retriever


def test_source_registry_contains_official_sources(client):
    response = client.get('/api/sources')
    assert response.status_code == 200
    slugs = {x['slug'] for x in response.json()}
    assert {'gastat','sama','data-gov-sa','world-bank'} <= slugs
    assert 'peda-demo' not in slugs


def test_rag_retrieves_verified_gdp_indicator(client):
    db = SessionLocal()
    try:
        results = retriever.retrieve_indicators(db, 'GDP growth in Saudi Arabia', limit=3)
        assert results
        assert results[0].indicator.indicator_id == 'NY.GDP.MKTP.KD.ZG'
        assert results[0].indicator.verification_status == 'verified'
    finally:
        db.close()


def test_data_status_reports_live_mode(client):
    response = client.get('/api/data/status')
    assert response.status_code == 200
    body = response.json()
    assert body['mode'] == 'live'
    assert body['verified_indicators'] >= 4
    assert body['ready'] is True

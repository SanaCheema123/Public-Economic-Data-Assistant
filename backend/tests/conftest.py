from __future__ import annotations

import os
from pathlib import Path

TEST_DB = Path('/tmp/peda_pytest.db')
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ['DATABASE_URL'] = f'sqlite:///{TEST_DB}'
os.environ['AI_MODE'] = 'deterministic'
os.environ['DATA_MODE'] = 'live'
os.environ['DATA_SYNC_ON_STARTUP'] = 'false'
os.environ['DATA_BACKGROUND_REFRESH'] = 'false'
os.environ['AUTO_CREATE_TABLES'] = 'true'
os.environ['JWT_SECRET'] = 'pytest-secret-that-is-not-used-outside-tests'
os.environ['RATE_LIMIT_PER_MINUTE'] = '1000'

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database.session import SessionLocal
from app.models.entities import RetrievalDocument
from app.services.connectors.ingestion import ingest_indicator_records


FIXTURES = [
    ("NY.GDP.MKTP.KD.ZG", "GDP Growth", "معدل نمو الناتج المحلي الإجمالي", "%", "Economy", [(2019, 0.8), (2020, -4.1), (2021, 3.9), (2022, 8.7), (2023, 4.2)], ["gdp", "growth", "الناتج", "النمو"]),
    ("SL.UEM.TOTL.ZS", "Unemployment Rate", "معدل البطالة", "%", "Labor Market", [(2019, 8.0), (2020, 8.7), (2021, 8.2), (2022, 7.9), (2023, 7.1)], ["unemployment", "labor", "البطالة", "العمل"]),
    ("FP.CPI.TOTL.ZG", "Inflation Rate", "معدل التضخم", "%", "Prices", [(2019, -2.1), (2020, 3.4), (2021, 3.1), (2022, 2.5), (2023, 2.3)], ["inflation", "cpi", "التضخم", "الأسعار"]),
    ("SP.POP.GROW", "Population Growth", "معدل نمو السكان", "%", "Population", [(2019, 1.2), (2020, 0.7), (2021, 1.0), (2022, 1.4), (2023, 1.6)], ["population", "growth", "السكان", "نمو"]),
]


def seed_verified_test_data() -> None:
    db = SessionLocal()
    try:
        for code, en, ar, unit, category, values, keywords in FIXTURES:
            out = ingest_indicator_records(
                db,
                source_slug='world-bank',
                dataset_slug='test-' + code.lower().replace('.', '-'),
                dataset_name_en=f'World Development Indicators — {en}',
                dataset_name_ar=f'مؤشرات التنمية العالمية — {ar}',
                source_url=f'https://data.worldbank.org/indicator/{code}?locations=SA',
                indicator_code=code,
                indicator_name_en=en,
                indicator_name_ar=ar,
                description_en=f'Verified test fixture using the schema of World Bank indicator {code}.',
                description_ar=f'بيانات اختبار موثقة وفق مخطط مؤشر البنك الدولي {code}.',
                unit=unit,
                frequency='Annual',
                category=category,
                records=[{'date': year, 'value': value} for year, value in values],
                replace_values=True,
                verification_status='verified',
            )
            doc = db.scalar(select(RetrievalDocument).where(RetrievalDocument.kind == 'indicator', RetrievalDocument.ref_id == out['indicator_id']))
            if doc:
                doc.keywords = keywords
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope='session')
def client():
    with TestClient(app) as c:
        seed_verified_test_data()
        yield c


@pytest.fixture
def account(client: TestClient):
    email = 'researcher@example.com'
    password = 'StrongPass123!'
    response = client.post('/api/auth/register', json={'full_name': 'Research User', 'email': email, 'password': password})
    if response.status_code == 409:
        response = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert response.status_code in {200, 201}
    return {'email': email, 'password': password, 'user': response.json()['user']}

from __future__ import annotations

import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.seed import seed_source_registry
from app.models.entities import Indicator, Source
from app.services.connectors.base import ConnectorResult
from app.services.live_data import WORLD_BANK_INDICATORS, sync_world_bank_live_data


def test_live_sync_ingests_verified_records_without_demo(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'live.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    seed_source_registry(db)

    async def fake_fetch(self, indicator_code, start_year=2000, end_year=2030, country='SAU', **kwargs):
        return ConnectorResult(
            True,
            'world-bank',
            records=[
                {'date': '2024', 'value': 1.25, 'indicator': indicator_code},
                {'date': '2025', 'value': 2.5, 'indicator': indicator_code},
            ],
            metadata={'url': f'https://api.worldbank.org/v2/country/SAU/indicator/{indicator_code}', 'lastupdated': '2026-01-01'},
        )

    async def fake_metadata(self, indicator_code):
        return ConnectorResult(
            True,
            'world-bank',
            records=[{'sourceNote': f'Official description for {indicator_code}', 'sourceOrganization': 'World Bank'}],
            metadata={},
        )

    monkeypatch.setattr('app.services.live_data.WorldBankConnector.fetch', fake_fetch)
    monkeypatch.setattr('app.services.live_data.WorldBankConnector.fetch_metadata', fake_metadata)

    try:
        result = asyncio.run(sync_world_bank_live_data(db, force=True))
        assert result['ok'] is True
        assert result['synced_indicators'] == len(WORLD_BANK_INDICATORS)
        indicators = db.scalars(select(Indicator)).all()
        assert len(indicators) == len(WORLD_BANK_INDICATORS)
        assert all(i.verification_status == 'verified' for i in indicators)
        assert db.scalar(select(Source).where(Source.source_type == 'demo')) is None
    finally:
        db.close()
        engine.dispose()


def test_partial_live_sync_is_retried_before_refresh_window(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'partial.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    seed_source_registry(db)
    failing_code = WORLD_BANK_INDICATORS[0].code
    calls = {spec.code: 0 for spec in WORLD_BANK_INDICATORS}

    async def flaky_fetch(self, indicator_code, start_year=2000, end_year=2030, country='SAU', **kwargs):
        calls[indicator_code] += 1
        if indicator_code == failing_code and calls[indicator_code] == 1:
            return ConnectorResult(False, 'world-bank', error='temporary upstream failure')
        return ConnectorResult(
            True,
            'world-bank',
            records=[{'date': '2025', 'value': 1.0, 'indicator': indicator_code}],
            metadata={'url': f'https://api.worldbank.org/v2/country/SAU/indicator/{indicator_code}', 'lastupdated': '2026-01-01'},
        )

    async def fake_metadata(self, indicator_code):
        return ConnectorResult(True, 'world-bank', records=[{'sourceNote': indicator_code, 'sourceOrganization': 'World Bank'}])

    monkeypatch.setattr('app.services.live_data.WorldBankConnector.fetch', flaky_fetch)
    monkeypatch.setattr('app.services.live_data.WorldBankConnector.fetch_metadata', fake_metadata)

    try:
        first = asyncio.run(sync_world_bank_live_data(db, force=True))
        assert first['synced_indicators'] == len(WORLD_BANK_INDICATORS) - 1
        second = asyncio.run(sync_world_bank_live_data(db, force=False))
        assert second.get('skipped') is not True
        assert calls[failing_code] == 2
        assert second['ready'] is True
    finally:
        db.close()
        engine.dispose()


def test_gastat_live_headlines_are_ingested_and_preferred(monkeypatch, tmp_path):
    from app.services.live_data import sync_gastat_headlines
    from app.services.dashboard_service import dashboard_payload

    engine = create_engine(f"sqlite:///{tmp_path / 'gastat.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    seed_source_registry(db)

    async def fake_headlines(self, **kwargs):
        return ConnectorResult(
            True,
            'gastat',
            records=[
                {'indicator':'GASTAT.REAL_GDP_GROWTH','name_en':'Real GDP Growth','name_ar':'معدل نمو الناتج المحلي الإجمالي الحقيقي','unit':'%','category':'Economy','frequency':'Quarterly','date':'2026-06-30','value':-4.8,'period':'Real GDP Growth rate - Second Quarter 2026','source_url':'https://stats.gov.sa/en/'},
                {'indicator':'GASTAT.SAUDI_UNEMPLOYMENT','name_en':'Saudi Unemployment Rate','name_ar':'معدل البطالة بين السعوديين','unit':'%','category':'Labor Market','frequency':'Quarterly','date':'2026-03-31','value':6.4,'period':'Saudi unemployment, First quarter 2026','source_url':'https://stats.gov.sa/en/'},
                {'indicator':'GASTAT.CPI_INFLATION','name_en':'Inflation Rate','name_ar':'معدل التضخم','unit':'%','category':'Prices','frequency':'Monthly','date':'2026-07-31','value':1.8,'period':'Inflation, July 2026','source_url':'https://stats.gov.sa/en/'},
            ],
            metadata={'url':'https://stats.gov.sa/en/','official':True,'live':True},
        )

    monkeypatch.setattr('app.services.live_data.GastatConnector.fetch_headlines', fake_headlines)
    try:
        result = asyncio.run(sync_gastat_headlines(db, force=True))
        assert result['ok'] is True
        assert result['synced_indicators'] == 3
        gdp = db.scalar(select(Indicator).where(Indicator.indicator_id == 'GASTAT.REAL_GDP_GROWTH'))
        assert gdp is not None
        assert gdp.verification_status == 'verified'
        source = db.get(Source, gdp.source_id)
        assert source.slug == 'gastat'
        assert source.source_type == 'official'
        payload = dashboard_payload(db)
        assert payload['kpis'][0]['indicator_id'] == 'GASTAT.REAL_GDP_GROWTH'
        assert payload['kpis'][0]['value'] == -4.8
        assert payload['kpis'][0]['source']['official'] is True
        assert 'Second Quarter 2026' in payload['kpis'][0]['period_label']
        from app.services.rag.retrieval import retriever
        retrieved = retriever.retrieve_indicators(db, 'What is the latest GDP growth in Saudi Arabia?', limit=3)
        assert retrieved
        assert retrieved[0].indicator.indicator_id == 'GASTAT.REAL_GDP_GROWTH'
    finally:
        db.close()
        engine.dispose()

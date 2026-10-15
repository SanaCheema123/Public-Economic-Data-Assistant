#!/usr/bin/env python3
"""Import a documented CSV/JSON/XLSX file into the normalized indicator schema.

Example:
  PYTHONPATH=backend python scripts/ingest_file.py \
    --file ./download.csv --source gastat --source-url https://www.stats.gov.sa/... \
    --dataset-slug official-gdp --dataset-name-en "National Accounts" --dataset-name-ar "الحسابات القومية" \
    --indicator-code GASTAT_REAL_GDP_GROWTH --indicator-name-en "Real GDP Growth" --indicator-name-ar "نمو الناتج المحلي الحقيقي" \
    --description-en "Annual real GDP growth" --description-ar "النمو السنوي للناتج المحلي الحقيقي" \
    --unit % --frequency Annual --category Economy --date-column year --value-column value --replace

Only use --verified after you have confirmed the file and source URL are official and the column mapping is correct.
"""
import argparse, asyncio

from app.database.session import SessionLocal
from app.services.connectors.file_connector import FileDataConnector
from app.services.connectors.ingestion import ingest_indicator_records


async def main():
    p=argparse.ArgumentParser()
    for name in ['file','source','source-url','dataset-slug','dataset-name-en','dataset-name-ar','indicator-code','indicator-name-en','indicator-name-ar','description-en','description-ar','unit','frequency','category','date-column','value-column']:
        p.add_argument(f'--{name}', required=True)
    p.add_argument('--region-column'); p.add_argument('--sector-column'); p.add_argument('--replace', action='store_true'); p.add_argument('--verified', action='store_true')
    a=p.parse_args()
    result=await FileDataConnector().fetch(path=a.file)
    if not result.ok: raise SystemExit(result.error)
    db=SessionLocal()
    try:
        summary=ingest_indicator_records(db, source_slug=a.source, dataset_slug=a.dataset_slug, dataset_name_en=a.dataset_name_en, dataset_name_ar=a.dataset_name_ar,
            source_url=a.source_url, indicator_code=a.indicator_code, indicator_name_en=a.indicator_name_en, indicator_name_ar=a.indicator_name_ar,
            description_en=a.description_en, description_ar=a.description_ar, unit=a.unit, frequency=a.frequency, category=a.category,
            records=result.records, date_column=a.date_column, value_column=a.value_column, region_column=a.region_column, sector_column=a.sector_column,
            replace_values=a.replace, verification_status='verified' if a.verified else 'unverified')
        print(summary)
    finally: db.close()

if __name__=='__main__': asyncio.run(main())

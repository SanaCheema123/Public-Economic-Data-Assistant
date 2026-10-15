#!/usr/bin/env python3
"""Connector smoke-runner.

Examples:
  PYTHONPATH=backend python scripts/ingest.py --source world-bank --indicator NY.GDP.MKTP.KD.ZG
  PYTHONPATH=backend python scripts/ingest.py --source gastat --url https://official.example/dataset.csv --format csv

This command prints a preview. Production ingestion should map validated fields into datasets,
indicators and indicator_values inside an audited admin job after source-specific schema review.
"""
import argparse
import asyncio
import json

from app.services.connectors import CONNECTORS


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, choices=sorted(CONNECTORS))
    parser.add_argument('--url')
    parser.add_argument('--format', default='json')
    parser.add_argument('--indicator')
    parser.add_argument('--start-year', type=int, default=2010)
    parser.add_argument('--end-year', type=int, default=2030)
    args = parser.parse_args()
    connector = CONNECTORS[args.source]
    if args.source == 'world-bank':
        if not args.indicator:
            parser.error('--indicator is required for world-bank')
        result = await connector.fetch(indicator_code=args.indicator, start_year=args.start_year, end_year=args.end_year)
    else:
        if not args.url:
            parser.error('--url is required for this source')
        result = await connector.fetch(url=args.url, format=args.format)
    print(json.dumps({'ok': result.ok, 'source': result.source, 'metadata': result.metadata, 'error': result.error, 'preview': result.records[:5]}, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    asyncio.run(main())

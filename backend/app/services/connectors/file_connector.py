from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.services.connectors.base import BaseDataConnector, ConnectorResult


class FileDataConnector(BaseDataConnector):
    source_slug = "local-import"

    async def fetch(self, path: str, **kwargs) -> ConnectorResult:
        file = Path(path)
        if not file.exists() or not file.is_file():
            return ConnectorResult(False, self.source_slug, error="File not found")
        try:
            suffix = file.suffix.lower()
            if suffix == '.csv':
                df = pd.read_csv(file)
            elif suffix in {'.xlsx', '.xlsm'}:
                df = pd.read_excel(file, engine='openpyxl')
            elif suffix == '.json':
                payload = json.loads(file.read_text(encoding='utf-8'))
                df = pd.DataFrame(payload if isinstance(payload, list) else payload.get('data', [payload]))
            else:
                return ConnectorResult(False, self.source_slug, error="Supported formats: CSV, JSON, XLSX")
            df = df.where(pd.notna(df), None)
            records = df.to_dict(orient='records')
            return ConnectorResult(True, self.source_slug, records=records, metadata={'path': str(file), 'count': len(records)})
        except Exception as exc:
            return ConnectorResult(False, self.source_slug, error=f"{type(exc).__name__}: file import failed")

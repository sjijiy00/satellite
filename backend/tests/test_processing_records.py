"""TEST ONLY local TIFF evidence, file retention and failure journals."""
import asyncio
import io
import json
import os
import time
import zipfile
from uuid import uuid4
import pytest
from fastapi import HTTPException
from app import processing, artifact_store
from app.pixel_policy import QualityError
from app.processing_worker import execute
from test_processing_foundation import raster_payload


@pytest.fixture(autouse=True)
def private_files(tmp_path, monkeypatch):
    monkeypatch.setattr(artifact_store, 'ROOT', tmp_path / 'artifacts')


@pytest.mark.parametrize('method', ['s2_quality', 'ndvi_change'])
def test_actual_files_carry_executed_not_proposed_record(tmp_path, method):
    result = execute(raster_payload(tmp_path, method=method), uuid4().hex)
    receipt = result['artifact']
    record = receipt['execution_record']
    assert record['source_mode'] == 'canonical_server_range'
    steps = {s['id']: s for s in record['steps']}
    assert steps['files']['status'] == 'completed'
    assert steps['composite']['status'] == steps['estimate']['status'] == 'skipped'
    assert steps['calibration']['status'] == 'completed'  # legacy engine also records radiometry
    assert all('url' not in s for s in record['inputs'])
    assert receipt['expires_at'] > receipt['created_at']


def test_retention_tracks_actual_missing_changed_and_expired_files(tmp_path):
    identifier = uuid4().hex
    result = execute(raster_payload(tmp_path), identifier)
    receipt = result['artifact']
    path = artifact_store.verified_download(identifier, receipt)
    assert artifact_store.retention(identifier, receipt)['state'] == 'available'
    with zipfile.ZipFile(path) as z:
        manifest = json.loads(z.read('manifest.json'))
        assert manifest['execution_record'] == receipt['execution_record']
        assert manifest['verified_after_disk_write']
    os.utime(path, (time.time() - artifact_store.TTL - 1,) * 2)
    assert artifact_store.retention(identifier, receipt)['state'] == 'expired'
    os.utime(path, None)
    with path.open('ab') as f: f.write(b'TEST_ONLY_CHANGED')
    assert artifact_store.retention(identifier, receipt)['state'] == 'changed'
    path.unlink()
    assert artifact_store.retention(identifier, receipt)['state'] == 'missing'


def test_failure_journal_is_not_completed_and_quality_remains_unknown(monkeypatch):
    async def fail(_query): raise QualityError('TEST ONLY canonical failure')
    monkeypatch.setattr(processing, 'prepare', fail)
    job = {'status': 'queued', 'owner': 'TEST_ONLY', 'events': [], 'artifact': None}
    asyncio.run(processing.execute(uuid4().hex, job, {'query': None}))
    assert job['status'] == 'failed'
    assert job['events'][0]['status'] == 'failed'
    assert job['result']['common_valid_percent_aoi'] is None
    assert job['artifact'] is None and job['expires_at']


def test_download_usage_failure_is_retryable_429_without_leaking_slot(monkeypatch):
    from app import media_access
    from app.provider_transfer import TransferError
    # Use the existing transfer exception constructor, no network or secrets.
    monkeypatch.setattr(processing, 'owned', lambda *_: {'status': 'succeeded', 'artifact': {'bytes': 1}, 'owner': 'TEST_ONLY'})
    monkeypatch.setattr(artifact_store, 'verified_download', lambda *_: None)
    released = []
    monkeypatch.setattr(media_access, 'enter', lambda: None)
    monkeypatch.setattr(media_access, 'leave', lambda: released.append(True))
    def limit(*_): raise TransferError('rate_limited')
    monkeypatch.setattr(media_access, 'charge_many', limit)
    with pytest.raises(HTTPException) as error:
        processing.download_response(uuid4().hex, None)
    assert error.value.status_code == 429 and released == [True]

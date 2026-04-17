import json
import os
import tempfile

import pytest

from src.state import ProcessedRecord


@pytest.fixture
def state_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestProcessedRecord:
    def test_fresh_init_writes_first_run_at(self, state_dir):
        path = os.path.join(state_dir, "processed.json")
        record = ProcessedRecord.load(path)

        assert os.path.exists(path)
        assert record.first_run_at > 0
        assert len(record.processed_file_ids) == 0

    def test_round_trip_load_modify_save(self, state_dir):
        path = os.path.join(state_dir, "processed.json")
        record = ProcessedRecord.load(path)
        original_first_run = record.first_run_at

        record.add_processed("F001")
        record.add_processed("F002")
        record.save()

        reloaded = ProcessedRecord.load(path)
        assert reloaded.first_run_at == original_first_run
        assert reloaded.is_processed("F001")
        assert reloaded.is_processed("F002")
        assert not reloaded.is_processed("F999")

    def test_first_run_at_never_overwritten(self, state_dir):
        path = os.path.join(state_dir, "processed.json")
        record = ProcessedRecord.load(path)
        original_first_run = record.first_run_at

        record.add_processed("F001")
        record.save()

        reloaded = ProcessedRecord.load(path)
        reloaded.add_processed("F002")
        reloaded.save()

        final = ProcessedRecord.load(path)
        assert final.first_run_at == original_first_run

    def test_add_processed_is_idempotent(self, state_dir):
        path = os.path.join(state_dir, "processed.json")
        record = ProcessedRecord.load(path)

        record.add_processed("F001")
        record.add_processed("F001")
        record.add_processed("F001")
        record.save()

        reloaded = ProcessedRecord.load(path)
        assert len(reloaded.processed_file_ids) == 1

    def test_atomic_write_no_partial_file(self, state_dir):
        path = os.path.join(state_dir, "processed.json")
        record = ProcessedRecord.load(path)
        record.add_processed("F001")
        record.save()

        # Verify the file is valid JSON after save
        with open(path) as f:
            data = json.load(f)
        assert "first_run_at" in data
        assert "F001" in data["processed_file_ids"]

        # No .tmp files should remain
        tmp_files = [f for f in os.listdir(state_dir) if f.endswith(".tmp")]
        assert len(tmp_files) == 0

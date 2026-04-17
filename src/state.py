import json
import os
import tempfile
import time
from datetime import datetime, timezone


class ProcessedRecord:
    def __init__(self, first_run_at: float, processed_file_ids: set, last_run_at: str | None, path: str):
        self.first_run_at = first_run_at
        self._processed_file_ids = set(processed_file_ids)
        self.last_run_at = last_run_at
        self._path = path

    @classmethod
    def load(cls, path: str) -> "ProcessedRecord":
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            return cls(
                first_run_at=data["first_run_at"],
                processed_file_ids=set(data.get("processed_file_ids", [])),
                last_run_at=data.get("last_run_at"),
                path=path,
            )

        record = cls(
            first_run_at=time.time(),
            processed_file_ids=set(),
            last_run_at=None,
            path=path,
        )
        record.save()
        return record

    def is_processed(self, file_id: str) -> bool:
        return file_id in self._processed_file_ids

    def add_processed(self, file_id: str) -> None:
        self._processed_file_ids.add(file_id)

    @property
    def processed_file_ids(self) -> set:
        return set(self._processed_file_ids)

    def save(self) -> None:
        self.last_run_at = datetime.now(timezone.utc).isoformat()
        data = {
            "first_run_at": self.first_run_at,
            "processed_file_ids": sorted(self._processed_file_ids),
            "last_run_at": self.last_run_at,
        }
        dir_name = os.path.dirname(self._path) or "."
        tmp_fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            os.replace(tmp_path, self._path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

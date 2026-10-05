from src import config, worker


def test_run_once_does_nothing_when_awards_disabled(monkeypatch):
    monkeypatch.setattr(config, "COIN_AWARDS_ENABLED", False)

    def fail_fetch(*args, **kwargs):
        raise AssertionError("inbox must not be read while awards are disabled")

    monkeypatch.setattr(worker.inbox, "fetch_pending", fail_fetch)
    worker.run_once()


def test_run_once_processes_rows_when_awards_enabled(monkeypatch):
    monkeypatch.setattr(config, "COIN_AWARDS_ENABLED", True)
    processed = []
    monkeypatch.setattr(worker.inbox, "fetch_pending", lambda: [("row-1", {}, 0)])
    monkeypatch.setattr(worker, "_process_row", lambda *row: processed.append(row))
    worker.run_once()
    assert processed == [("row-1", {}, 0)]

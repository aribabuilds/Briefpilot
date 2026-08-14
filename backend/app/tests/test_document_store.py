from app.repositories.document_store import InMemoryDocumentStore


def test_put_then_get_returns_the_stored_content_and_type() -> None:
    store = InMemoryDocumentStore()
    store.put("job-1", content=b"raw bytes", content_type="image/png")
    assert store.get("job-1") == (b"raw bytes", "image/png")


def test_get_returns_none_for_an_unknown_job_id() -> None:
    store = InMemoryDocumentStore()
    assert store.get("does-not-exist") is None


def test_documents_for_different_jobs_do_not_collide() -> None:
    store = InMemoryDocumentStore()
    store.put("job-1", content=b"first", content_type="image/png")
    store.put("job-2", content=b"second", content_type="application/pdf")
    assert store.get("job-1") == (b"first", "image/png")
    assert store.get("job-2") == (b"second", "application/pdf")


def test_put_overwrites_a_previous_entry_for_the_same_job_id() -> None:
    store = InMemoryDocumentStore()
    store.put("job-1", content=b"old", content_type="image/png")
    store.put("job-1", content=b"new", content_type="image/jpeg")
    assert store.get("job-1") == (b"new", "image/jpeg")


def test_delete_removes_the_stored_content() -> None:
    store = InMemoryDocumentStore()
    store.put("job-1", content=b"raw bytes", content_type="image/png")
    store.delete("job-1")
    assert store.get("job-1") is None


def test_delete_is_idempotent_for_an_unknown_job_id() -> None:
    store = InMemoryDocumentStore()
    store.delete("does-not-exist")  # must not raise


def test_delete_does_not_affect_other_jobs() -> None:
    store = InMemoryDocumentStore()
    store.put("job-1", content=b"first", content_type="image/png")
    store.put("job-2", content=b"second", content_type="application/pdf")
    store.delete("job-1")
    assert store.get("job-1") is None
    assert store.get("job-2") == (b"second", "application/pdf")

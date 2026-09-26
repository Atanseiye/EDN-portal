from server.store import BetaStore


def add(store, identity, external=True):
    return store.add(
        tester_identity=identity,
        display_name=None,
        affiliation="External Lab",
        role="ML Engineer",
        features=["python_sdk", "playground"],
        rating=4,
        useful=True,
        blocker=None,
        notes=None,
        external_tester=external,
        consent=True,
    )


def test_unreviewed_external_feedback_does_not_count(tmp_path):
    store = BetaStore(str(tmp_path / "beta.sqlite3"))
    evidence_id = add(store, "dev1@example.com")
    stats = store.stats()
    assert stats["pending_external_submissions"] == 1
    assert stats["unique_verified_external_beta_testers"] == 0
    assert stats["beta_target_met"] is False

    store.verify_external(evidence_id)
    stats = store.stats()
    assert stats["unique_verified_external_beta_testers"] == 1
    assert stats["pending_external_submissions"] == 0


def test_unique_verified_external_beta_testers(tmp_path):
    store = BetaStore(str(tmp_path / "beta.sqlite3"))
    first = add(store, "dev1@example.com")
    duplicate = add(store, "dev1@example.com")
    second = add(store, "dev2@example.com")

    store.verify_external(first)
    store.verify_external(duplicate)
    assert store.stats()["unique_verified_external_beta_testers"] == 1

    store.verify_external(second)
    stats = store.stats()
    assert stats["unique_verified_external_beta_testers"] == 2
    assert stats["beta_target_met"] is True


def test_internal_tester_cannot_be_verified_as_external(tmp_path):
    store = BetaStore(str(tmp_path / "beta.sqlite3"))
    evidence_id = add(store, "team@example.com", external=False)
    assert store.stats()["unique_verified_external_beta_testers"] == 0

    try:
        store.verify_external(evidence_id)
        assert False, "Internal evidence should not be externally verifiable"
    except KeyError:
        pass

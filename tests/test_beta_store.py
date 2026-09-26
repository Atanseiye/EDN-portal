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


def test_unique_external_beta_testers(tmp_path):
    store = BetaStore(str(tmp_path / "beta.sqlite3"))
    add(store, "dev1@example.com")
    add(store, "dev1@example.com")
    assert store.stats()["unique_external_beta_testers"] == 1
    assert store.stats()["beta_target_met"] is False

    add(store, "dev2@example.com")
    stats = store.stats()
    assert stats["unique_external_beta_testers"] == 2
    assert stats["beta_target_met"] is True


def test_internal_tester_does_not_count(tmp_path):
    store = BetaStore(str(tmp_path / "beta.sqlite3"))
    add(store, "team@example.com", external=False)
    assert store.stats()["unique_external_beta_testers"] == 0

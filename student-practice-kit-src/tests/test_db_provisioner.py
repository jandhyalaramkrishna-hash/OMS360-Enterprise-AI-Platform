"""
Tests for the parts of launcher/db_provisioner.py that don't require an
actual Windows machine or a real mysqld binary: environment-variable
construction (must match app/config.py's exact names) and the
provisioned/not-provisioned marker check. The mysqld process-management
functions (start_mysqld, provision, _apply_sql_file) are Windows-specific
and depend on the bundled binary that only exists after build.bat runs on
a real Windows machine - see build/README.md's manual verification
checklist for those.
"""

from launcher import db_provisioner


def test_env_overrides_matches_app_config_variable_names(monkeypatch):
    """These exact names (OMS360_DB_HOST etc.) must match what
    app/config.py's ApplicationSettings reads via os.getenv - that
    coupling is intentional and is how this module avoids touching
    app/config.py at all. If app/config.py's env var names ever change,
    this test (not app/config.py) is what should fail first.

    Isolated from real machine port state: env_overrides() now reports
    whatever get_active_port() resolves to (2026-07-31 fix - falls back
    past LOCAL_DB_PORT if it's occupied, e.g. by a leftover mysqld.exe),
    which is correct behavior but means the raw port number is no longer
    guaranteed to be 33071 on a machine that happens to have something
    already bound to it when this test runs. Resetting the cache and
    forcing every port to read as free makes the assertion deterministic
    again without weakening what it actually checks."""
    monkeypatch.setattr(db_provisioner, "_active_port", None)
    monkeypatch.setattr(db_provisioner, "_is_port_free", lambda port: True)

    env = db_provisioner.env_overrides()

    assert env["OMS360_DB_HOST"] == "127.0.0.1"
    assert env["OMS360_DB_PORT"] == str(db_provisioner.LOCAL_DB_PORT)
    assert env["OMS360_DB_USER"] == "root"
    assert env["OMS360_DB_NAME"] == "oms360_db"
    assert env["OMS360_KAFKA_ENABLED"] == "false"
    assert env["OMS360_DOCKER_MODE"] == "false"


def test_local_db_port_is_not_the_default_mysql_port():
    # Deliberately not 3306 - must not collide with a student's own MySQL,
    # if they happen to have one installed already.
    assert db_provisioner.LOCAL_DB_PORT != 3306


def test_is_provisioned_false_when_nothing_set_up(tmp_path, monkeypatch):
    monkeypatch.setattr(db_provisioner, "_persistent_root", lambda: tmp_path)
    assert db_provisioner.is_provisioned() is False


def test_is_provisioned_true_after_marker_file_written(tmp_path, monkeypatch):
    monkeypatch.setattr(db_provisioner, "_persistent_root", lambda: tmp_path)
    marker_dir = tmp_path / "mysql" / "data"
    marker_dir.mkdir(parents=True)
    (marker_dir / ".oms360_provisioned").write_text("ok")
    assert db_provisioner.is_provisioned() is True


def test_provision_raises_clearly_when_bundle_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(db_provisioner, "_persistent_root", lambda: tmp_path)
    monkeypatch.setattr(db_provisioner, "_bundle_resource_dir", lambda: tmp_path / "nonexistent")

    import pytest
    with pytest.raises(db_provisioner.ProvisioningError, match="mysql-portable"):
        db_provisioner.provision()

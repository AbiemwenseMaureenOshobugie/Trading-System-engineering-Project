"""MS-0.17 ownership adapter tests."""

from trading_system.runtime.ownership import FileRuntimeOwnership


def test_runtime_identity_maps_to_deterministic_lock_path(tmp_path):
    first = FileRuntimeOwnership(runtime_id="aster-test", lock_directory=tmp_path)
    second = FileRuntimeOwnership(runtime_id="aster-test", lock_directory=tmp_path)
    assert first.path == second.path


def test_two_owners_cannot_hold_same_runtime_identity(tmp_path):
    first = FileRuntimeOwnership(runtime_id="aster-test", lock_directory=tmp_path)
    second = FileRuntimeOwnership(runtime_id="aster-test", lock_directory=tmp_path)
    first.acquire()
    try:
        try:
            second.acquire()
        except Exception:
            pass
        else:
            raise AssertionError("second owner acquired the same runtime identity")
    finally:
        first.release()

"""Phase 0 smoke test: the package imports and declares a version."""


def test_import():
    import graphready

    assert graphready.__version__

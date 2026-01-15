def test_import() -> None:
    import homelab

    assert homelab
    assert homelab.version

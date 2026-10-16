from backend import privacy


def test_site_terms_are_versioned_with_privacy_and_preserved_in_snapshot(monkeypatch):
    monkeypatch.setattr(privacy, 'config', lambda db: dict(privacy.DEFAULTS))
    current = privacy.notice(None)
    assert current['terms']
    assert 'Uso do site' in [section['title'] for section in current['sections']]
    for section in current['terms'] + current['sections']:
        assert section['text'] in current['snapshot']
    monkeypatch.setattr(privacy, 'config', lambda db: {**privacy.DEFAULTS, 'controller': 'Outro responsável'})
    assert privacy.notice(None)['version'] != current['version']

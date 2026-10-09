"""CLI startup must report real composition gaps without crashing."""

from trading_system.__main__ import main


def test_main_reports_unimplemented_composition_capabilities(capsys, monkeypatch):
    monkeypatch.delenv("TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.delenv("ASTER_INSTRUMENTS", raising=False)

    exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ASTER runtime composition gap:" in captured.err
    assert "observation_history_policy" in captured.err
    assert "risk_governance_qualification_context" in captured.err
    assert captured.out == ""

from __future__ import annotations

from trading_bot.config.loader import load_settings


def test_mode_specific_config_inherits_default_settings(tmp_path, monkeypatch) -> None:
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "default.yaml").write_text(
        """
application:
  mode: BACKTEST
trading:
  symbol: GBPUSD
  broker_symbol: GBPUSD
  timeframe: H1
backtest:
  initial_balance: 25000
""",
        encoding="utf-8",
    )
    (configs / "backtest.yaml").write_text(
        """
application:
  mode: BACKTEST
trading:
  timeframe: M15
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    settings = load_settings("configs/backtest.yaml")

    assert settings.trading.symbol == "GBPUSD"
    assert settings.trading.broker_symbol == "GBPUSD"
    assert settings.trading.timeframe == "M15"
    assert settings.backtest.initial_balance == 25000

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from trading_bot.application.backtest_runner import BacktestRunner
from trading_bot.application.live_runner import LiveRunner
from trading_bot.application.paper_runner import PaperRunner
from trading_bot.config.models import Settings
from trading_bot.domain import BacktestResult, Candle, Trade
from trading_bot.execution.mt5_gateway import MT5Gateway
from trading_bot.market_data import load_candles_from_csv
from trading_bot.persistence import TradingBotDatabase
from trading_bot.risk import RuntimeRiskState
from trading_bot.strategies import StrategyDescriptor, default_strategy_registry


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "EURUSD Trading Bot",
        "settings": "Settings",
        "backtest": "Backtest",
        "paper": "Paper",
        "live": "Live",
        "report": "Report Center",
        "language": "Language",
        "mt5_settings": "MetaTrader 5 Settings",
        "terminal_path": "Terminal Path",
        "browse": "Browse",
        "server": "Server",
        "login": "Login",
        "password": "Password",
        "expected_account": "Expected Account",
        "status": "Status",
        "test_connection": "Test Connection",
        "disconnected": "Disconnected",
        "connecting": "Connecting...",
        "connected": "Connected",
        "connection_failed": "Connection failed",
        "strategy": "Strategy",
        "symbol": "Symbol",
        "broker_symbol": "Broker Symbol",
        "timeframe": "Timeframe",
        "risk_percent": "Risk %",
        "max_spread": "Max Spread",
        "strong_candle_min_body_pips": "Strong Candle Min Body (pips)",
        "strong_candle_max_body_pips": "Strong Candle Max Body (pips)",
        "strong_candle_max_total_wick_pips": "Strong Candle Max Total Wick (pips)",
        "strong_candle_take_profit_pips": "Strong Candle TP (pips)",
        "strong_candle_stop_loss_pips": "Strong Candle SL (pips)",
        "balance": "Balance",
        "leverage": "Leverage",
        "start_date": "Start Date",
        "end_date": "End Date",
        "spread_points": "Spread Points",
        "slippage_points": "Slippage Points",
        "commission": "Commission / Lot",
        "data": "Data",
        "run_backtest": "Run Backtest",
        "backtest_log_ready": "Backtest is ready. Connect MT5 history or select a CSV candle file.",
        "running_backtest": "Running backtest...",
        "backtest_failed": "Backtest failed",
        "completed": "completed",
        "paper_title": "Paper Trading",
        "paper_explain": (
            "Paper mode reads real MT5 candles and ticks, generates real-time signals, "
            "and simulates entries/exits. It never calls order_send, so no real order is sent."
        ),
        "start_paper": "Start Paper",
        "stop_paper": "Stop Paper",
        "paper_started": "Paper mode started. Real orders are disabled.",
        "paper_looping": "Paper worker is running on closed candles. Real orders are disabled.",
        "live_title": "Live Trading",
        "live_warning": (
            "Live mode can send real market orders after all safety switches pass. "
            "Use a demo account first."
        ),
        "start_live": "Start Live",
        "stop_live": "Stop Live",
        "live_starting": "Starting live safety checks...",
        "live_blocked": "Live blocked",
        "live_ready": "Live startup checks passed.",
        "live_gated": "Live loop is intentionally gated in this demo build until demo-account rollout.",
        "history": "History",
        "trades": "Trades",
        "stress_tests": "Stress Tests",
        "entry": "Entry",
        "exit": "Exit",
        "side": "Side",
        "volume": "Volume",
        "entry_price": "Entry Price",
        "exit_price": "Exit Price",
        "net_pnl": "Net P&L",
        "signal_reason": "Signal Reason",
        "indicators": "Indicators",
        "exit_reason": "Exit Reason",
        "scenario": "Scenario",
        "profit_factor": "Profit Factor",
        "select_terminal": "Select terminal64.exe",
        "select_csv": "Select candle CSV",
        "strategy_description": "Strategy Description",
        "live_log_ready": "Live mode is idle. Configure parameters, then press Start Live.",
        "paper_log_ready": "Paper mode is idle. It is safe because it does not send orders.",
        "stopped": "Stopped.",
        "live_worker_stopped": "Live worker stopped.",
    },
    "fa": {
        "app_title": "ربات معاملاتی EURUSD",
        "settings": "تنظیمات",
        "backtest": "بک تست",
        "paper": "پیپر",
        "live": "لایو",
        "report": "گزارش",
        "language": "زبان",
        "mt5_settings": "تنظیمات متاتریدر 5",
        "terminal_path": "مسیر ترمینال",
        "browse": "انتخاب",
        "server": "سرور",
        "login": "نام کاربری",
        "password": "پسورد",
        "expected_account": "اکانت مورد انتظار",
        "status": "وضعیت",
        "test_connection": "تست اتصال",
        "disconnected": "قطع",
        "connecting": "در حال اتصال...",
        "connected": "متصل",
        "connection_failed": "اتصال ناموفق",
        "strategy": "استراتژی",
        "symbol": "نماد",
        "broker_symbol": "نماد بروکر",
        "timeframe": "تایم فریم",
        "risk_percent": "ریسک %",
        "max_spread": "حداکثر اسپرد",
        "strong_candle_min_body_pips": "حداقل بدنه کندل قوی (پیپ)",
        "strong_candle_max_body_pips": "حداکثر بدنه کندل قوی (پیپ)",
        "strong_candle_max_total_wick_pips": "حداکثر جمع شدو بالا و پایین (پیپ)",
        "strong_candle_take_profit_pips": "تی پی کندل قوی (پیپ)",
        "strong_candle_stop_loss_pips": "اس ال کندل قوی (پیپ)",
        "balance": "بالانس",
        "leverage": "لوریج",
        "start_date": "تاریخ شروع",
        "end_date": "تاریخ پایان",
        "spread_points": "اسپرد پوینت",
        "slippage_points": "اسلیپیج پوینت",
        "commission": "کمیسیون هر لات",
        "data": "داده",
        "run_backtest": "شروع بک تست",
        "backtest_log_ready": "بک تست آماده است. از دیتای نمونه استفاده کن یا فایل CSV کندل انتخاب کن.",
        "running_backtest": "در حال اجرای بک تست...",
        "backtest_failed": "بک تست ناموفق",
        "completed": "کامل شد",
        "paper_title": "پیپر تریدینگ",
        "paper_explain": (
            "حالت پیپر کندل و تیک واقعی را از متاتریدر می خواند، سیگنال واقعی می سازد، "
            "ولی ورود و خروج را شبیه سازی می کند. در این حالت هیچ سفارش واقعی ارسال نمی شود."
        ),
        "start_paper": "شروع پیپر",
        "stop_paper": "توقف پیپر",
        "paper_started": "حالت پیپر شروع شد. سفارش واقعی غیرفعال است.",
        "paper_looping": "پردازشگر پیپر روی کندل های بسته شده فعال است. سفارش واقعی ارسال نمی شود.",
        "live_title": "معامله لایو",
        "live_warning": (
            "حالت لایو بعد از عبور از قفل های ایمنی می تواند سفارش واقعی ارسال کند. "
            "اول روی اکانت دمو تست شود."
        ),
        "start_live": "شروع لایو",
        "stop_live": "توقف لایو",
        "live_starting": "در حال بررسی قفل های ایمنی لایو...",
        "live_blocked": "لایو متوقف شد",
        "live_ready": "بررسی شروع لایو موفق بود.",
        "live_gated": "لوپ لایو در این نسخه نمایشی تا rollout اکانت دمو عمدا قفل است.",
        "history": "سوابق",
        "trades": "معاملات",
        "stress_tests": "استرس تست",
        "entry": "ورود",
        "exit": "خروج",
        "side": "جهت",
        "volume": "حجم",
        "entry_price": "قیمت ورود",
        "exit_price": "قیمت خروج",
        "net_pnl": "سود/ضرر خالص",
        "signal_reason": "دلیل سیگنال",
        "indicators": "اندیکاتورها",
        "exit_reason": "دلیل خروج",
        "scenario": "سناریو",
        "profit_factor": "فاکتور سود",
        "select_terminal": "انتخاب terminal64.exe",
        "select_csv": "انتخاب فایل CSV کندل",
        "strategy_description": "توضیح استراتژی",
        "live_log_ready": "لایو آماده است. پارامترها را تنظیم کن و Start Live را بزن.",
        "paper_log_ready": "پیپر آماده است. امن است چون سفارش واقعی ارسال نمی کند.",
        "stopped": "متوقف شد.",
        "live_worker_stopped": "پردازشگر لایو متوقف شد.",
    },
}


def launch_ui(settings: Settings) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ModuleNotFoundError:
        print("PySide6 is not installed. Run: python -m pip install -e .")
        return 1

    app = QApplication([])
    window = MainWindow(settings)
    window.show()
    return app.exec()


class MainWindow:
    def __new__(cls, settings: Settings) -> "MainWindow":
        from PySide6.QtWidgets import QMainWindow

        class _MainWindow(QMainWindow):
            def __init__(self, settings: Settings) -> None:
                super().__init__()
                self.settings = settings
                self.registry = default_strategy_registry()
                self.language = "en"
                self.current_result: BacktestResult | None = None
                self.database = TradingBotDatabase(settings.ui.database_path)
                self.database.initialize()
                self.labels: dict[str, list[Any]] = {}
                self.buttons: dict[str, Any] = {}
                self.groups: dict[str, Any] = {}
                self._auto_broker_symbol: dict[str, bool] = {}
                self.log_events: dict[str, list[str]] = {
                    "backtest": ["backtest_log_ready"],
                    "paper": ["paper_log_ready"],
                    "live": ["live_log_ready"],
                }
                self.setWindowTitle(self._t("app_title"))
                self.resize(1380, 880)
                self._build()
                self._apply_theme()
                self._load_strategy_lists()
                self._refresh_history()
                self._apply_language()

            def _t(self, key: str) -> str:
                return TRANSLATIONS[self.language].get(key, key)

            def _build(self) -> None:
                from PySide6.QtCore import QDate, Qt
                from PySide6.QtWidgets import (
                    QComboBox,
                    QDateEdit,
                    QDoubleSpinBox,
                    QFileDialog,
                    QFormLayout,
                    QGridLayout,
                    QGroupBox,
                    QHBoxLayout,
                    QLabel,
                    QLineEdit,
                    QListWidget,
                    QPushButton,
                    QSpinBox,
                    QSplitter,
                    QTableWidget,
                    QTabWidget,
                    QTextEdit,
                    QVBoxLayout,
                    QWidget,
                )

                self.tabs = QTabWidget()
                self.setCentralWidget(self.tabs)

                self.settings_tab = QWidget()
                settings_layout = QGridLayout(self.settings_tab)
                self.groups["mt5_settings"] = QGroupBox()
                connection_form = QFormLayout(self.groups["mt5_settings"])
                self.language_combo = QComboBox()
                self.language_combo.addItem("English", "en")
                self.language_combo.addItem("فارسی", "fa")
                self.language_combo.setCurrentIndex(0)
                self.language_combo.currentIndexChanged.connect(self._language_changed)
                self.terminal_path = QLineEdit()
                self.terminal_path.setReadOnly(True)
                self.terminal_browse_button = QPushButton()
                self.terminal_browse_button.clicked.connect(lambda: self._browse_terminal(QFileDialog))
                terminal_row = QHBoxLayout()
                terminal_row.addWidget(self.terminal_path)
                terminal_row.addWidget(self.terminal_browse_button)
                self.server = QLineEdit()
                self.login = QLineEdit()
                self.password = QLineEdit()
                self.password.setEchoMode(QLineEdit.Password)
                self.expected_account = QLineEdit()
                self.connection_status = QLabel()
                self.connection_status.setObjectName("statusLabel")
                self.test_connection_button = QPushButton()
                self.test_connection_button.clicked.connect(self._test_connection)
                self._add_row(connection_form, "language", self.language_combo)
                self._add_row(connection_form, "terminal_path", terminal_row)
                self._add_row(connection_form, "server", self.server)
                self._add_row(connection_form, "login", self.login)
                self._add_row(connection_form, "password", self.password)
                self._add_row(connection_form, "expected_account", self.expected_account)
                self._add_row(connection_form, "status", self.connection_status)
                connection_form.addRow("", self.test_connection_button)
                settings_layout.addWidget(self.groups["mt5_settings"], 0, 0)
                self.powered_by_label = QLabel(
                    "Powered by Milad Hashemi\nتوسعه داده شده توسط میلاد هاشمی"
                )
                self.powered_by_label.setObjectName("poweredByLabel")
                settings_layout.addWidget(self.powered_by_label, 1, 0)

                self.backtest_tab = QWidget()
                backtest_layout = QGridLayout(self.backtest_tab)
                self.groups["backtest"] = QGroupBox()
                backtest_form = QFormLayout(self.groups["backtest"])
                self.backtest_strategy_combo = QComboBox()
                self.backtest_symbol = QLineEdit(self.settings.trading.symbol)
                self.backtest_broker_symbol = QLineEdit(self.settings.trading.broker_symbol)
                self.backtest_timeframe = _timeframe_combo(QComboBox(), self.settings.trading.timeframe)
                self.backtest_risk_percent = _double_spin(0.01, 10, 2, float(self.settings.risk.risk_per_trade_percent))
                self.backtest_max_spread = _spin(1, 500, self.settings.execution.maximum_spread_points)
                self.backtest_strong_body = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_min_body_pips)
                )
                self.backtest_strong_max_body = _double_spin(
                    0.1, 2000, 1, float(self.settings.strategy.strong_candle_max_body_pips)
                )
                self.backtest_strong_wick = _double_spin(
                    0, 500, 1, float(self.settings.strategy.strong_candle_max_total_wick_pips)
                )
                self.backtest_strong_tp = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_take_profit_pips)
                )
                self.backtest_strong_sl = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_stop_loss_pips)
                )
                self.balance_input = _double_spin(100, 100_000_000, 2, float(self.settings.backtest.initial_balance))
                self.leverage_input = _spin(1, 3000, self.settings.backtest.leverage)
                today = QDate.currentDate()
                default_start_date = today.addMonths(-6)
                default_end_date = today.addDays(-1)
                self.backtest_start_date = QDateEdit(default_start_date)
                self.backtest_start_date.setCalendarPopup(True)
                self.backtest_start_date.setDisplayFormat("yyyy-MM-dd")
                self.backtest_end_date = QDateEdit(default_end_date)
                self.backtest_end_date.setCalendarPopup(True)
                self.backtest_end_date.setDisplayFormat("yyyy-MM-dd")
                self.spread_input = _spin(0, 500, self.settings.backtest.default_spread_points)
                self.slippage_input = _spin(0, 100, self.settings.backtest.slippage_points)
                self.commission_input = _double_spin(
                    0,
                    1000,
                    2,
                    float(self.settings.backtest.commission_per_lot_round_turn),
                )
                self.csv_path = QLineEdit()
                self.csv_path.setPlaceholderText("CSV")
                self.csv_browse_button = QPushButton()
                self.csv_browse_button.clicked.connect(lambda: self._browse_csv(QFileDialog))
                csv_row = QHBoxLayout()
                csv_row.addWidget(self.csv_path)
                csv_row.addWidget(self.csv_browse_button)
                self.run_backtest_button = QPushButton()
                self.run_backtest_button.clicked.connect(self._run_backtest)
                self._add_row(backtest_form, "strategy", self.backtest_strategy_combo)
                self._add_row(backtest_form, "symbol", self.backtest_symbol)
                self._add_row(backtest_form, "broker_symbol", self.backtest_broker_symbol)
                self._add_row(backtest_form, "timeframe", self.backtest_timeframe)
                self._add_row(backtest_form, "risk_percent", self.backtest_risk_percent)
                self._add_row(backtest_form, "max_spread", self.backtest_max_spread)
                self.backtest_strong_body_label = self._add_row(
                    backtest_form,
                    "strong_candle_min_body_pips",
                    self.backtest_strong_body,
                )
                self.backtest_strong_max_body_label = self._add_row(
                    backtest_form,
                    "strong_candle_max_body_pips",
                    self.backtest_strong_max_body,
                )
                self.backtest_strong_wick_label = self._add_row(
                    backtest_form,
                    "strong_candle_max_total_wick_pips",
                    self.backtest_strong_wick,
                )
                self.backtest_strong_tp_label = self._add_row(
                    backtest_form,
                    "strong_candle_take_profit_pips",
                    self.backtest_strong_tp,
                )
                self.backtest_strong_sl_label = self._add_row(
                    backtest_form,
                    "strong_candle_stop_loss_pips",
                    self.backtest_strong_sl,
                )
                self._add_row(backtest_form, "balance", self.balance_input)
                self._add_row(backtest_form, "leverage", self.leverage_input)
                self._add_row(backtest_form, "start_date", self.backtest_start_date)
                self._add_row(backtest_form, "end_date", self.backtest_end_date)
                self._add_row(backtest_form, "spread_points", self.spread_input)
                self._add_row(backtest_form, "slippage_points", self.slippage_input)
                self._add_row(backtest_form, "commission", self.commission_input)
                self._add_row(backtest_form, "data", csv_row)
                backtest_form.addRow("", self.run_backtest_button)
                self.backtest_strategy_description = QTextEdit()
                self.backtest_strategy_description.setReadOnly(True)
                self.backtest_log = QTextEdit()
                self.backtest_log.setReadOnly(True)
                self._configure_log_widget(self.backtest_log)
                backtest_layout.addWidget(self.groups["backtest"], 0, 0)
                backtest_layout.addWidget(self._side_panel("strategy_description", self.backtest_strategy_description), 0, 1)
                backtest_layout.addWidget(self.backtest_log, 1, 0, 1, 2)
                self.backtest_strategy_combo.currentTextChanged.connect(self._backtest_strategy_changed)

                self.paper_tab = QWidget()
                paper_layout = QGridLayout(self.paper_tab)
                self.groups["paper"] = QGroupBox()
                paper_form = QFormLayout(self.groups["paper"])
                self.paper_strategy_combo = QComboBox()
                self.paper_symbol = QLineEdit(self.settings.trading.symbol)
                self.paper_broker_symbol = QLineEdit(self.settings.trading.broker_symbol)
                self.paper_timeframe = _timeframe_combo(QComboBox(), self.settings.trading.timeframe)
                self.paper_risk_percent = _double_spin(0.01, 10, 2, float(self.settings.risk.risk_per_trade_percent))
                self.paper_max_spread = _spin(1, 500, self.settings.execution.maximum_spread_points)
                self.paper_strong_body = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_min_body_pips)
                )
                self.paper_strong_max_body = _double_spin(
                    0.1, 2000, 1, float(self.settings.strategy.strong_candle_max_body_pips)
                )
                self.paper_strong_wick = _double_spin(
                    0, 500, 1, float(self.settings.strategy.strong_candle_max_total_wick_pips)
                )
                self.paper_strong_tp = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_take_profit_pips)
                )
                self.paper_strong_sl = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_stop_loss_pips)
                )
                self.paper_start_button = QPushButton()
                self.paper_start_button.clicked.connect(self._start_paper)
                self.paper_stop_button = QPushButton()
                self.paper_stop_button.setEnabled(False)
                self.paper_stop_button.clicked.connect(self._stop_paper)
                paper_buttons = QHBoxLayout()
                paper_buttons.addWidget(self.paper_start_button)
                paper_buttons.addWidget(self.paper_stop_button)
                self._add_row(paper_form, "strategy", self.paper_strategy_combo)
                self._add_row(paper_form, "symbol", self.paper_symbol)
                self._add_row(paper_form, "broker_symbol", self.paper_broker_symbol)
                self._add_row(paper_form, "timeframe", self.paper_timeframe)
                self._add_row(paper_form, "risk_percent", self.paper_risk_percent)
                self._add_row(paper_form, "max_spread", self.paper_max_spread)
                self.paper_strong_body_label = self._add_row(
                    paper_form,
                    "strong_candle_min_body_pips",
                    self.paper_strong_body,
                )
                self.paper_strong_max_body_label = self._add_row(
                    paper_form,
                    "strong_candle_max_body_pips",
                    self.paper_strong_max_body,
                )
                self.paper_strong_wick_label = self._add_row(
                    paper_form,
                    "strong_candle_max_total_wick_pips",
                    self.paper_strong_wick,
                )
                self.paper_strong_tp_label = self._add_row(
                    paper_form,
                    "strong_candle_take_profit_pips",
                    self.paper_strong_tp,
                )
                self.paper_strong_sl_label = self._add_row(
                    paper_form,
                    "strong_candle_stop_loss_pips",
                    self.paper_strong_sl,
                )
                paper_form.addRow("", paper_buttons)
                self.paper_explain = QTextEdit()
                self.paper_explain.setReadOnly(True)
                self.paper_log = QTextEdit()
                self.paper_log.setReadOnly(True)
                self._configure_log_widget(self.paper_log)
                paper_layout.addWidget(self.groups["paper"], 0, 0)
                paper_layout.addWidget(self.paper_explain, 0, 1)
                paper_layout.addWidget(self.paper_log, 1, 0, 1, 2)
                self.paper_strategy_combo.currentTextChanged.connect(
                    lambda value: self._update_strategy_parameter_visibility("paper", value)
                )

                self.live_tab = QWidget()
                live_layout = QGridLayout(self.live_tab)
                self.groups["live"] = QGroupBox()
                live_form = QFormLayout(self.groups["live"])
                self.live_strategy_combo = QComboBox()
                self.live_symbol = QLineEdit(self.settings.trading.symbol)
                self.live_broker_symbol = QLineEdit(self.settings.trading.broker_symbol)
                self.live_timeframe = _timeframe_combo(QComboBox(), self.settings.trading.timeframe)
                self.live_risk_percent = _double_spin(0.01, 10, 2, float(self.settings.risk.risk_per_trade_percent))
                self.live_max_spread = _spin(1, 500, self.settings.execution.maximum_spread_points)
                self.live_strong_body = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_min_body_pips)
                )
                self.live_strong_max_body = _double_spin(
                    0.1, 2000, 1, float(self.settings.strategy.strong_candle_max_body_pips)
                )
                self.live_strong_wick = _double_spin(
                    0, 500, 1, float(self.settings.strategy.strong_candle_max_total_wick_pips)
                )
                self.live_strong_tp = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_take_profit_pips)
                )
                self.live_strong_sl = _double_spin(
                    0.1, 1000, 1, float(self.settings.strategy.strong_candle_stop_loss_pips)
                )
                self.live_start_button = QPushButton()
                self.live_start_button.clicked.connect(self._start_live)
                self.live_stop_button = QPushButton()
                self.live_stop_button.setEnabled(False)
                self.live_stop_button.clicked.connect(self._stop_live)
                live_buttons = QHBoxLayout()
                live_buttons.addWidget(self.live_start_button)
                live_buttons.addWidget(self.live_stop_button)
                self._add_row(live_form, "strategy", self.live_strategy_combo)
                self._add_row(live_form, "symbol", self.live_symbol)
                self._add_row(live_form, "broker_symbol", self.live_broker_symbol)
                self._add_row(live_form, "timeframe", self.live_timeframe)
                self._add_row(live_form, "risk_percent", self.live_risk_percent)
                self._add_row(live_form, "max_spread", self.live_max_spread)
                self.live_strong_body_label = self._add_row(
                    live_form,
                    "strong_candle_min_body_pips",
                    self.live_strong_body,
                )
                self.live_strong_max_body_label = self._add_row(
                    live_form,
                    "strong_candle_max_body_pips",
                    self.live_strong_max_body,
                )
                self.live_strong_wick_label = self._add_row(
                    live_form,
                    "strong_candle_max_total_wick_pips",
                    self.live_strong_wick,
                )
                self.live_strong_tp_label = self._add_row(
                    live_form,
                    "strong_candle_take_profit_pips",
                    self.live_strong_tp,
                )
                self.live_strong_sl_label = self._add_row(
                    live_form,
                    "strong_candle_stop_loss_pips",
                    self.live_strong_sl,
                )
                live_form.addRow("", live_buttons)
                self.live_warning = QTextEdit()
                self.live_warning.setReadOnly(True)
                self.live_log = QTextEdit()
                self.live_log.setReadOnly(True)
                self._configure_log_widget(self.live_log)
                live_layout.addWidget(self.groups["live"], 0, 0)
                live_layout.addWidget(self.live_warning, 0, 1)
                live_layout.addWidget(self.live_log, 1, 0, 1, 2)
                self.live_strategy_combo.currentTextChanged.connect(
                    lambda value: self._update_strategy_parameter_visibility("live", value)
                )
                self._connect_symbol_pair("backtest", self.backtest_symbol, self.backtest_broker_symbol)
                self._connect_symbol_pair("paper", self.paper_symbol, self.paper_broker_symbol)
                self._connect_symbol_pair("live", self.live_symbol, self.live_broker_symbol)

                self.report_tab = QWidget()
                report_layout = QGridLayout(self.report_tab)
                splitter = QSplitter(Qt.Orientation.Horizontal)
                left_report = QWidget()
                left_layout = QVBoxLayout(left_report)
                self.summary_grid = QGridLayout()
                left_layout.addLayout(self.summary_grid)
                self.equity_chart = ChartWidget("Equity")
                self.drawdown_chart = ChartWidget("Drawdown %")
                left_layout.addWidget(self.equity_chart)
                left_layout.addWidget(self.drawdown_chart)
                right_report = QWidget()
                right_layout = QVBoxLayout(right_report)
                self.history_label = QLabel()
                self.history_list = QListWidget()
                self.trades_label = QLabel()
                self.trade_table = QTableWidget(0, 13)
                self.stress_label = QLabel()
                self.stress_table = QTableWidget(0, 4)
                right_layout.addWidget(self.history_label)
                right_layout.addWidget(self.history_list)
                right_layout.addWidget(self.trades_label)
                right_layout.addWidget(self.trade_table)
                right_layout.addWidget(self.stress_label)
                right_layout.addWidget(self.stress_table)
                splitter.addWidget(left_report)
                splitter.addWidget(right_report)
                splitter.setStretchFactor(0, 3)
                splitter.setStretchFactor(1, 2)
                report_layout.addWidget(splitter, 0, 0)

                self.tabs.addTab(self.settings_tab, "")
                self.tabs.addTab(self.backtest_tab, "")
                self.tabs.addTab(self.paper_tab, "")
                self.tabs.addTab(self.live_tab, "")
                self.tabs.addTab(self.report_tab, "")

            def _side_panel(self, title_key: str, widget: Any) -> Any:
                from PySide6.QtWidgets import QGroupBox, QVBoxLayout

                group = QGroupBox()
                self.groups[title_key] = group
                layout = QVBoxLayout(group)
                layout.addWidget(widget)
                return group

            def _add_row(self, form: Any, key: str, widget_or_layout: Any) -> Any:
                from PySide6.QtWidgets import QLabel

                label = QLabel()
                self.labels.setdefault(key, []).append(label)
                form.addRow(label, widget_or_layout)
                return label

            def _configure_log_widget(self, widget: Any) -> None:
                widget.document().setMaximumBlockCount(100)

            def _apply_theme(self) -> None:
                self.setStyleSheet(
                    """
                    QMainWindow { background: #111827; color: #e5e7eb; }
                    QWidget { color: #e5e7eb; font-size: 13px; }
                    QTabWidget::pane { border: 1px solid #374151; }
                    QTabBar::tab { background: #1f2937; padding: 10px 18px; border: 1px solid #374151; }
                    QTabBar::tab:selected { background: #0f766e; }
                    QGroupBox { border: 1px solid #374151; border-radius: 6px; margin-top: 14px; padding: 12px; }
                    QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
                    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                        background: #0b1220; border: 1px solid #374151; border-radius: 6px; padding: 7px;
                        selection-background-color: #0f766e;
                    }
                    QPushButton {
                        background: #0f766e; border: 0; border-radius: 6px; padding: 9px 14px; font-weight: 600;
                    }
                    QPushButton:hover { background: #0d9488; }
                    QPushButton:disabled { background: #374151; color: #9ca3af; }
                    QTableWidget { background: #0b1220; gridline-color: #374151; border: 1px solid #374151; }
                    QHeaderView::section { background: #1f2937; padding: 7px; border: 1px solid #374151; }
                    QListWidget { background: #0b1220; border: 1px solid #374151; border-radius: 6px; }
                    #statusLabel { color: #fbbf24; font-weight: 700; }
                    #poweredByLabel {
                        color: #9ca3af;
                        font-size: 12px;
                        padding: 10px 4px;
                    }
                    QCalendarWidget {
                        background: #0b1220;
                        color: #e5e7eb;
                        border: 1px solid #374151;
                    }
                    QCalendarWidget QWidget {
                        background: #0b1220;
                        color: #e5e7eb;
                    }
                    QCalendarWidget QToolButton {
                        background: #1f2937;
                        color: #f9fafb;
                        border: 1px solid #374151;
                        border-radius: 4px;
                        padding: 5px;
                    }
                    QCalendarWidget QToolButton:hover {
                        background: #0f766e;
                    }
                    QCalendarWidget QMenu {
                        background: #111827;
                        color: #f9fafb;
                        border: 1px solid #374151;
                    }
                    QCalendarWidget QSpinBox {
                        background: #111827;
                        color: #f9fafb;
                        border: 1px solid #374151;
                        border-radius: 4px;
                        padding: 3px;
                    }
                    QCalendarWidget QAbstractItemView:enabled {
                        background: #111827;
                        color: #f9fafb;
                        selection-background-color: #0f766e;
                        selection-color: #ffffff;
                        alternate-background-color: #0b1220;
                    }
                    QCalendarWidget QAbstractItemView:disabled {
                        color: #6b7280;
                    }
                    """
                )

            def _load_strategy_lists(self) -> None:
                for combo in (
                    self.backtest_strategy_combo,
                    self.paper_strategy_combo,
                    self.live_strategy_combo,
                ):
                    combo.clear()
                    for descriptor in self.registry.all():
                        combo.addItem(descriptor.strategy_id)
                    combo.setCurrentText(self.settings.strategy.strategy_id)
                self._strategy_changed(
                    self.settings.strategy.strategy_id,
                    self.backtest_strategy_description,
                )
                self._update_strategy_parameter_visibility(
                    "backtest",
                    self.backtest_strategy_combo.currentText(),
                )
                self._update_strategy_parameter_visibility(
                    "paper",
                    self.paper_strategy_combo.currentText(),
                )
                self._update_strategy_parameter_visibility(
                    "live",
                    self.live_strategy_combo.currentText(),
                )

            def _backtest_strategy_changed(self, strategy_id: str) -> None:
                self._strategy_changed(strategy_id, self.backtest_strategy_description)
                self._update_strategy_parameter_visibility("backtest", strategy_id)

            def _strategy_changed(self, strategy_id: str, target: Any) -> None:
                descriptor = self.registry.get(strategy_id)
                target.setPlainText(_strategy_text(descriptor, self.language))

            def _update_strategy_parameter_visibility(self, target: str, strategy_id: str) -> None:
                is_strong_candle = strategy_id == "strong_candle_v1"
                rows = {
                    "backtest": (
                        (self.backtest_strong_body_label, self.backtest_strong_body),
                        (self.backtest_strong_max_body_label, self.backtest_strong_max_body),
                        (self.backtest_strong_wick_label, self.backtest_strong_wick),
                        (self.backtest_strong_tp_label, self.backtest_strong_tp),
                        (self.backtest_strong_sl_label, self.backtest_strong_sl),
                    ),
                    "paper": (
                        (self.paper_strong_body_label, self.paper_strong_body),
                        (self.paper_strong_max_body_label, self.paper_strong_max_body),
                        (self.paper_strong_wick_label, self.paper_strong_wick),
                        (self.paper_strong_tp_label, self.paper_strong_tp),
                        (self.paper_strong_sl_label, self.paper_strong_sl),
                    ),
                    "live": (
                        (self.live_strong_body_label, self.live_strong_body),
                        (self.live_strong_max_body_label, self.live_strong_max_body),
                        (self.live_strong_wick_label, self.live_strong_wick),
                        (self.live_strong_tp_label, self.live_strong_tp),
                        (self.live_strong_sl_label, self.live_strong_sl),
                    ),
                }[target]
                for label, widget in rows:
                    label.setVisible(is_strong_candle)
                    widget.setVisible(is_strong_candle)

            def _connect_symbol_pair(self, target: str, symbol_edit: Any, broker_edit: Any) -> None:
                self._auto_broker_symbol[target] = _is_same_symbol_or_empty(
                    broker_edit.text(),
                    symbol_edit.text(),
                )
                symbol_edit.textEdited.connect(
                    lambda text, target=target, broker_edit=broker_edit: self._symbol_text_edited(
                        target,
                        broker_edit,
                        text,
                    )
                )
                broker_edit.textEdited.connect(
                    lambda text, target=target, symbol_edit=symbol_edit: self._broker_symbol_text_edited(
                        target,
                        symbol_edit,
                        text,
                    )
                )

            def _symbol_text_edited(self, target: str, broker_edit: Any, text: str) -> None:
                if self._auto_broker_symbol.get(target, True):
                    broker_edit.setText(text.strip())

            def _broker_symbol_text_edited(self, target: str, symbol_edit: Any, text: str) -> None:
                self._auto_broker_symbol[target] = _is_same_symbol_or_empty(text, symbol_edit.text())

            def _language_changed(self) -> None:
                self.language = self.language_combo.currentData()
                self._apply_language()

            def _apply_language(self) -> None:
                self.setWindowTitle(self._t("app_title"))
                tab_keys = ["settings", "backtest", "paper", "live", "report"]
                for index, key in enumerate(tab_keys):
                    self.tabs.setTabText(index, self._t(key))
                for key, labels in self.labels.items():
                    for label in labels:
                        label.setText(self._t(key))
                for key, group in self.groups.items():
                    group.setTitle(self._t(key))
                self.terminal_browse_button.setText(self._t("browse"))
                self.csv_browse_button.setText(self._t("browse"))
                self.test_connection_button.setText(self._t("test_connection"))
                self.run_backtest_button.setText(self._t("run_backtest"))
                self.paper_start_button.setText(self._t("start_paper"))
                self.paper_stop_button.setText(self._t("stop_paper"))
                self.live_start_button.setText(self._t("start_live"))
                self.live_stop_button.setText(self._t("stop_live"))
                self.paper_explain.setPlainText(self._t("paper_explain"))
                self.live_warning.setPlainText(self._t("live_warning"))
                if not self.connection_status.text():
                    self.connection_status.setText(self._t("disconnected"))
                self._render_log_events("backtest")
                self._render_log_events("paper")
                self._render_log_events("live")
                self.history_label.setText(self._t("history"))
                self.trades_label.setText(self._t("trades"))
                self.stress_label.setText(self._t("stress_tests"))
                self.trade_table.setHorizontalHeaderLabels(
                    [
                        self._t("entry"),
                        self._t("exit"),
                        self._t("symbol"),
                        self._t("side"),
                        self._t("volume"),
                        self._t("entry_price"),
                        self._t("exit_price"),
                        "SL",
                        "TP",
                        self._t("net_pnl"),
                        self._t("signal_reason"),
                        self._t("indicators"),
                        self._t("exit_reason"),
                    ]
                )
                self.stress_table.setHorizontalHeaderLabels(
                    [
                        self._t("scenario"),
                        self._t("net_pnl"),
                        self._t("profit_factor"),
                        self._t("trades"),
                    ]
                )
                if self.backtest_strategy_combo.currentText():
                    self._strategy_changed(
                        self.backtest_strategy_combo.currentText(),
                        self.backtest_strategy_description,
                    )

            def _browse_terminal(self, file_dialog: Any) -> None:
                path, _ = file_dialog.getOpenFileName(
                    self,
                    self._t("select_terminal"),
                    "",
                    "MetaTrader terminal (terminal64.exe terminal.exe);;Executable (*.exe);;All Files (*)",
                )
                if path:
                    self.terminal_path.setText(path)

            def _browse_csv(self, file_dialog: Any) -> None:
                path, _ = file_dialog.getOpenFileName(
                    self,
                    self._t("select_csv"),
                    "",
                    "CSV Files (*.csv);;All Files (*)",
                )
                if path:
                    self.csv_path.setText(path)

            def _test_connection(self) -> None:
                self.connection_status.setText(self._t("connecting"))
                try:
                    gateway = self._make_gateway()
                    gateway.connect()
                    account = gateway.get_account()
                    gateway.disconnect()
                    self.connection_status.setText(
                        f"{self._t('connected')}: {account.login} / {account.server} / Equity {account.equity}"
                    )
                except Exception as exc:
                    self.connection_status.setText(f"{self._t('connection_failed')}: {exc}")

            def _run_backtest(self) -> None:
                from PySide6.QtCore import QThread, Signal

                class _BacktestThread(QThread):
                    finished_result = Signal(object, object)
                    failed = Signal(str)

                    def __init__(
                        self,
                        settings: Settings,
                        csv_path: str,
                        terminal_path: str,
                        login: int | None,
                        password: str,
                        server: str,
                    ) -> None:
                        super().__init__()
                        self.settings = settings
                        self.csv_path = csv_path
                        self.terminal_path = terminal_path
                        self.login = login
                        self.password = password
                        self.server = server

                    def run(self) -> None:
                        try:
                            candles = (
                                load_candles_from_csv(self.csv_path)
                                if self.csv_path
                                else _mt5_candles_for_settings(
                                    self.settings,
                                    self.terminal_path,
                                    self.login,
                                    self.password,
                                    self.server,
                                )
                            )
                            result = BacktestRunner(self.settings).run(candles, persist=True)
                            self.finished_result.emit(result, candles)
                        except Exception as exc:
                            self.failed.emit(str(exc))

                if getattr(self, "backtest_thread", None) is not None and self.backtest_thread.isRunning():
                    self._append_log_event("backtest", "running_backtest")
                    return

                self._sync_backtest_settings()
                login = int(self.login.text()) if self.login.text().strip() else None
                self._clear_report()
                self.run_backtest_button.setEnabled(False)
                data_source = "CSV" if self.csv_path.text().strip() else "MT5 history"
                self._set_log_events(
                    "backtest",
                    [
                        (
                            f"{self._t('running_backtest')} "
                            f"{self.settings.trading.symbol} "
                            f"({self.settings.trading.broker_symbol}) "
                            f"{self.settings.trading.timeframe} | {data_source}"
                        )
                    ],
                )
                self.backtest_thread = _BacktestThread(
                    copy.deepcopy(self.settings),
                    self.csv_path.text().strip(),
                    self.terminal_path.text().strip(),
                    login,
                    self.password.text(),
                    self.server.text().strip(),
                )
                self.backtest_thread.finished_result.connect(self._backtest_finished)
                self.backtest_thread.failed.connect(self._backtest_failed)
                self.backtest_thread.finished.connect(self._backtest_thread_finished)
                self.backtest_thread.finished.connect(self.backtest_thread.deleteLater)
                self.backtest_thread.start()

            def _backtest_thread_finished(self) -> None:
                self.run_backtest_button.setEnabled(True)
                self.backtest_thread = None

            def _backtest_finished(self, result: BacktestResult, candles: list[Candle]) -> None:
                del candles
                self.current_result = result
                self._render_result(result)
                self._refresh_history()
                self.tabs.setCurrentWidget(self.report_tab)
                self._set_log_events(
                    "backtest",
                    [
                        (
                            f"Run {result.run_id} {self._t('completed')} | "
                            f"{result.symbol} {result.timeframe} | {len(result.trades)} trades"
                        )
                    ],
                )

            def _backtest_failed(self, reason: str) -> None:
                self._set_log_events("backtest", [f"{self._t('backtest_failed')}: {reason}"])

            def _start_paper(self) -> None:
                from PySide6.QtCore import QThread, Signal

                class _PaperThread(QThread):
                    log_line = Signal(str)
                    failed = Signal(str)

                    def __init__(
                        self,
                        settings: Settings,
                        terminal_path: str,
                        login: int | None,
                        password: str,
                        server: str,
                    ) -> None:
                        super().__init__()
                        self.settings = settings
                        self.terminal_path = terminal_path
                        self.login = login
                        self.password = password
                        self.server = server

                    def run(self) -> None:
                        gateway = MT5Gateway(
                            settings=self.settings,
                            terminal_path=self.terminal_path,
                            login=self.login,
                            password=self.password,
                            server=self.server,
                        )
                        try:
                            gateway.connect()
                            account = gateway.get_account()
                            state = RuntimeRiskState(
                                start_of_day_equity=account.equity,
                                equity_peak=account.equity,
                            )
                            runner = PaperRunner(self.settings, gateway)
                            self.log_line.emit("paper_looping")
                            last_repeated_message = ""
                            while not self.isInterruptionRequested():
                                result = runner.run_once(state)
                                message = result.reason
                                if not (
                                    message == "candle already processed"
                                    and message == last_repeated_message
                                ):
                                    self.log_line.emit(message)
                                last_repeated_message = message
                                self.msleep(5000)
                        except Exception as exc:
                            self.failed.emit(str(exc))
                        finally:
                            try:
                                gateway.disconnect()
                            except Exception:
                                pass

                if getattr(self, "paper_thread", None) is not None and self.paper_thread.isRunning():
                    self._append_log_event("paper", "paper_looping")
                    return
                self._sync_mode_settings("PAPER")
                login = int(self.login.text()) if self.login.text().strip() else None
                self.paper_start_button.setEnabled(False)
                self.paper_stop_button.setEnabled(True)
                self._set_log_events("paper", ["paper_started"])
                self.paper_thread = _PaperThread(
                    copy.deepcopy(self.settings),
                    self.terminal_path.text().strip(),
                    login,
                    self.password.text(),
                    self.server.text().strip(),
                )
                self.paper_thread.log_line.connect(lambda line: self._append_log_event("paper", line))
                self.paper_thread.failed.connect(self._paper_failed)
                self.paper_thread.finished.connect(self._paper_finished)
                self.paper_thread.finished.connect(self.paper_thread.deleteLater)
                self.paper_thread.start()

            def _paper_failed(self, reason: str) -> None:
                self._append_log_event("paper", f"{self._t('backtest_failed')}: {reason}")
                self.paper_start_button.setEnabled(True)
                self.paper_stop_button.setEnabled(False)

            def _paper_finished(self) -> None:
                if self.paper_stop_button.isEnabled():
                    self._append_log_event("paper", "stopped")
                self.paper_start_button.setEnabled(True)
                self.paper_stop_button.setEnabled(False)
                self.paper_thread = None

            def _stop_paper(self) -> None:
                if getattr(self, "paper_thread", None) is not None and self.paper_thread.isRunning():
                    self.paper_thread.requestInterruption()
                    self.paper_thread.wait(3000)
                self.paper_start_button.setEnabled(True)
                self.paper_stop_button.setEnabled(False)
                self._append_log_event("paper", "stopped")

            def _start_live(self) -> None:
                from PySide6.QtCore import QThread, Signal

                class _LiveThread(QThread):
                    log_line = Signal(str)
                    failed = Signal(str)

                    def __init__(
                        self,
                        settings: Settings,
                        terminal_path: str,
                        login: int | None,
                        password: str,
                        server: str,
                    ) -> None:
                        super().__init__()
                        self.settings = settings
                        self.terminal_path = terminal_path
                        self.login = login
                        self.password = password
                        self.server = server

                    def run(self) -> None:
                        gateway = MT5Gateway(
                            settings=self.settings,
                            terminal_path=self.terminal_path,
                            login=self.login,
                            password=self.password,
                            server=self.server,
                        )
                        try:
                            gateway.connect()
                            account = gateway.get_account()
                            state = RuntimeRiskState(
                                start_of_day_equity=account.equity,
                                equity_peak=account.equity,
                            )
                            runner = LiveRunner(self.settings, gateway)
                            check = runner.startup_check()
                            if not check.allowed:
                                self.failed.emit(check.reason)
                                return
                            self.log_line.emit("live_ready")
                            last_repeated_message = ""
                            while not self.isInterruptionRequested():
                                message = runner.run_once(state)
                                if not (
                                    message.startswith("No new closed candle")
                                    and message == last_repeated_message
                                ):
                                    self.log_line.emit(message)
                                last_repeated_message = message
                                self.msleep(5000)
                        except Exception as exc:
                            self.failed.emit(str(exc))
                        finally:
                            try:
                                gateway.disconnect()
                            except Exception:
                                pass

                if getattr(self, "live_thread", None) is not None and self.live_thread.isRunning():
                    self._append_log_event("live", "live_starting")
                    return
                self._sync_mode_settings("LIVE")
                self._set_log_events("live", ["live_starting"])
                self.live_start_button.setEnabled(False)
                self.live_stop_button.setEnabled(True)
                login = int(self.login.text()) if self.login.text().strip() else None
                self.live_thread = _LiveThread(
                    copy.deepcopy(self.settings),
                    self.terminal_path.text().strip(),
                    login,
                    self.password.text(),
                    self.server.text().strip(),
                )
                self.live_thread.log_line.connect(lambda line: self._append_log_event("live", line))
                self.live_thread.failed.connect(self._live_failed)
                self.live_thread.finished.connect(self._live_finished)
                self.live_thread.finished.connect(self.live_thread.deleteLater)
                self.live_thread.start()

            def _live_failed(self, reason: str) -> None:
                self._append_log_event("live", f"{self._t('live_blocked')}: {reason}")
                self.live_start_button.setEnabled(True)
                self.live_stop_button.setEnabled(False)

            def _live_finished(self) -> None:
                if self.live_stop_button.isEnabled():
                    self._append_log_event("live", "live_worker_stopped")
                self.live_start_button.setEnabled(True)
                self.live_stop_button.setEnabled(False)
                self.live_thread = None

            def _stop_live(self) -> None:
                if getattr(self, "live_thread", None) is not None and self.live_thread.isRunning():
                    self.live_thread.requestInterruption()
                    self.live_thread.wait(3000)
                self.live_start_button.setEnabled(True)
                self.live_stop_button.setEnabled(False)
                self._append_log_event("live", "stopped")

            def closeEvent(self, event: Any) -> None:
                for thread_name in ("live_thread", "paper_thread", "backtest_thread"):
                    thread = getattr(self, thread_name, None)
                    if thread is not None and thread.isRunning():
                        thread.requestInterruption()
                        thread.wait(3000)
                event.accept()

            def _log_widget(self, target: str) -> Any:
                if target == "backtest":
                    return self.backtest_log
                if target == "paper":
                    return self.paper_log
                if target == "live":
                    return self.live_log
                raise KeyError(target)

            def _set_log_events(self, target: str, events: list[str]) -> None:
                self.log_events[target] = events[-100:]
                self._render_log_events(target)

            def _append_log_event(self, target: str, event: str) -> None:
                events = self.log_events.setdefault(target, [])
                events.append(event)
                if len(events) > 100:
                    del events[: len(events) - 100]
                self._render_log_events(target)

            def _render_log_events(self, target: str) -> None:
                from PySide6.QtGui import QTextCursor

                widget = self._log_widget(target)
                lines = [self._t(event) if event in TRANSLATIONS[self.language] else event for event in self.log_events.get(target, [])]
                widget.setPlainText("\n".join(lines))
                widget.moveCursor(QTextCursor.MoveOperation.End)

            def _make_gateway(self) -> MT5Gateway:
                login = int(self.login.text()) if self.login.text().strip() else None
                return MT5Gateway(
                    settings=self.settings,
                    terminal_path=self.terminal_path.text().strip(),
                    login=login,
                    password=self.password.text(),
                    server=self.server.text().strip(),
                )

            def _sync_backtest_settings(self) -> None:
                self.settings.application.mode = "BACKTEST"
                self.settings.strategy.strategy_id = self.backtest_strategy_combo.currentText()
                self.settings.trading.symbol, self.settings.trading.broker_symbol = (
                    self._read_symbol_pair("backtest", self.backtest_symbol, self.backtest_broker_symbol)
                )
                self.settings.trading.timeframe = self.backtest_timeframe.currentText()
                self.settings.risk.risk_per_trade_percent = Decimal(str(self.backtest_risk_percent.value()))
                self.settings.execution.maximum_spread_points = self.backtest_max_spread.value()
                self.settings.strategy.strong_candle_min_body_pips = Decimal(
                    str(self.backtest_strong_body.value())
                )
                self.settings.strategy.strong_candle_max_body_pips = Decimal(
                    str(self.backtest_strong_max_body.value())
                )
                self.settings.strategy.strong_candle_max_total_wick_pips = Decimal(
                    str(self.backtest_strong_wick.value())
                )
                self.settings.strategy.strong_candle_take_profit_pips = Decimal(
                    str(self.backtest_strong_tp.value())
                )
                self.settings.strategy.strong_candle_stop_loss_pips = Decimal(
                    str(self.backtest_strong_sl.value())
                )
                self.settings.backtest.initial_balance = Decimal(str(self.balance_input.value()))
                self.settings.backtest.leverage = self.leverage_input.value()
                self.settings.backtest.start_date = self.backtest_start_date.date().toString("yyyy-MM-dd")
                self.settings.backtest.end_date = self.backtest_end_date.date().toString("yyyy-MM-dd")
                self.settings.backtest.default_spread_points = self.spread_input.value()
                self.settings.backtest.slippage_points = self.slippage_input.value()
                self.settings.backtest.commission_per_lot_round_turn = Decimal(
                    str(self.commission_input.value())
                )

            def _sync_mode_settings(self, mode: str) -> None:
                self.settings.application.mode = mode
                if mode == "PAPER":
                    strategy = self.paper_strategy_combo.currentText()
                    symbol, broker_symbol = self._read_symbol_pair(
                        "paper",
                        self.paper_symbol,
                        self.paper_broker_symbol,
                    )
                    timeframe = self.paper_timeframe.currentText()
                    risk = self.paper_risk_percent.value()
                    max_spread = self.paper_max_spread.value()
                    strong_body = self.paper_strong_body.value()
                    strong_max_body = self.paper_strong_max_body.value()
                    strong_wick = self.paper_strong_wick.value()
                    strong_tp = self.paper_strong_tp.value()
                    strong_sl = self.paper_strong_sl.value()
                else:
                    strategy = self.live_strategy_combo.currentText()
                    symbol, broker_symbol = self._read_symbol_pair(
                        "live",
                        self.live_symbol,
                        self.live_broker_symbol,
                    )
                    timeframe = self.live_timeframe.currentText()
                    risk = self.live_risk_percent.value()
                    max_spread = self.live_max_spread.value()
                    strong_body = self.live_strong_body.value()
                    strong_max_body = self.live_strong_max_body.value()
                    strong_wick = self.live_strong_wick.value()
                    strong_tp = self.live_strong_tp.value()
                    strong_sl = self.live_strong_sl.value()
                self.settings.strategy.strategy_id = strategy
                self.settings.trading.symbol = symbol
                self.settings.trading.broker_symbol = broker_symbol
                self.settings.trading.timeframe = timeframe
                self.settings.risk.risk_per_trade_percent = Decimal(str(risk))
                self.settings.execution.maximum_spread_points = max_spread
                self.settings.strategy.strong_candle_min_body_pips = Decimal(str(strong_body))
                self.settings.strategy.strong_candle_max_body_pips = Decimal(str(strong_max_body))
                self.settings.strategy.strong_candle_max_total_wick_pips = Decimal(str(strong_wick))
                self.settings.strategy.strong_candle_take_profit_pips = Decimal(str(strong_tp))
                self.settings.strategy.strong_candle_stop_loss_pips = Decimal(str(strong_sl))

            def _read_symbol_pair(self, target: str, symbol_edit: Any, broker_edit: Any) -> tuple[str, str]:
                symbol = symbol_edit.text().strip() or "EURUSD"
                broker_symbol = (
                    symbol
                    if self._auto_broker_symbol.get(target, True)
                    else broker_edit.text().strip() or symbol
                )
                symbol_edit.setText(symbol)
                broker_edit.setText(broker_symbol)
                return symbol, broker_symbol

            def _clear_report(self) -> None:
                _clear_layout(self.summary_grid)
                self.trade_table.setRowCount(0)
                self.stress_table.setRowCount(0)
                self.equity_chart.set_series([])
                self.drawdown_chart.set_series([])

            def _render_result(self, result: BacktestResult) -> None:
                from PySide6.QtWidgets import QLabel

                metrics = result.metrics
                summary_items = [
                    (self._t("symbol"), result.symbol),
                    (self._t("timeframe"), result.timeframe),
                    ("Net Profit", metrics.get("net_profit")),
                    ("Profit Factor", metrics.get("profit_factor")),
                    ("Max DD %", metrics.get("maximum_drawdown_percent")),
                    ("Win Rate %", metrics.get("win_rate_percent")),
                    ("Trades", metrics.get("total_trades")),
                    ("Final Balance", metrics.get("final_balance")),
                    ("Highest Equity", metrics.get("highest_equity")),
                    ("Lowest Equity", metrics.get("lowest_equity")),
                ]
                for index, (title, value) in enumerate(summary_items):
                    card = QLabel(f"{title}\n{_fmt(value)}")
                    card.setObjectName("summaryCard")
                    card.setStyleSheet(
                        "QLabel#summaryCard { background: #0b1220; border: 1px solid #374151; "
                        "border-radius: 6px; padding: 14px; font-size: 15px; font-weight: 700; }"
                    )
                    self.summary_grid.addWidget(card, index // 3, index % 3)
                self.equity_chart.set_series(result.equity_curve)
                self.drawdown_chart.set_series(result.drawdown_curve)
                self._render_trades(result.trades)
                self._render_stress(result.stress_results)

            def _render_trades(self, trades: list[Trade]) -> None:
                from PySide6.QtWidgets import QTableWidgetItem

                self.trade_table.setRowCount(len(trades))
                for row, trade in enumerate(trades):
                    values = [
                        trade.entry_time.isoformat(),
                        trade.exit_time.isoformat(),
                        trade.symbol,
                        trade.side.value,
                        trade.volume,
                        trade.entry_price,
                        trade.exit_price,
                        trade.stop_loss,
                        trade.take_profit,
                        trade.net_pnl,
                        trade.signal_reason,
                        _fmt_indicators(trade.signal_indicators),
                        trade.exit_reason,
                    ]
                    for col, value in enumerate(values):
                        self.trade_table.setItem(row, col, QTableWidgetItem(_fmt(value)))
                self.trade_table.resizeColumnsToContents()

            def _render_stress(self, rows: list[dict[str, Any]]) -> None:
                from PySide6.QtWidgets import QTableWidgetItem

                self.stress_table.setRowCount(len(rows))
                for row_index, row in enumerate(rows):
                    values = [
                        row.get("scenario"),
                        row.get("net_profit"),
                        row.get("profit_factor"),
                        row.get("total_trades"),
                    ]
                    for col, value in enumerate(values):
                        self.stress_table.setItem(row_index, col, QTableWidgetItem(_fmt(value)))
                self.stress_table.resizeColumnsToContents()

            def _refresh_history(self) -> None:
                self.history_list.clear()
                for row in self.database.list_backtest_runs():
                    metrics = row["metrics"]
                    self.history_list.addItem(
                        f"{row['run_id']} | {row['symbol']} {row['timeframe']} | {row['strategy_name']} | "
                        f"P&L {_fmt(metrics.get('net_profit'))} | Trades {metrics.get('total_trades')}"
                    )

        return _MainWindow(settings)


class ChartWidget:
    def __new__(cls, title: str) -> "ChartWidget":
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QPainter, QPen
        from PySide6.QtWidgets import QWidget

        class _ChartWidget(QWidget):
            def __init__(self, title: str) -> None:
                super().__init__()
                self.title = title
                self.series: list[tuple[Any, Decimal]] = []
                self.setMinimumHeight(220)

            def set_series(self, series: list[tuple[Any, Decimal]]) -> None:
                self.series = series
                self.update()

            def paintEvent(self, event: Any) -> None:
                del event
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                rect = self.rect().adjusted(12, 12, -12, -12)
                painter.fillRect(self.rect(), QColor("#0b1220"))
                painter.setPen(QPen(QColor("#374151"), 1))
                painter.drawRoundedRect(rect, 6, 6)
                painter.setPen(QPen(QColor("#e5e7eb"), 1))
                painter.drawText(rect.adjusted(10, 6, -10, -6), Qt.AlignmentFlag.AlignTop, self.title)
                if len(self.series) < 2:
                    return
                values = [float(value) for _, value in self.series]
                low = min(values)
                high = max(values)
                if high == low:
                    high += 1
                    low -= 1
                plot = rect.adjusted(16, 34, -16, -16)
                points: list[QPointF] = []
                for index, value in enumerate(values):
                    x = plot.left() + (plot.width() * index / max(1, len(values) - 1))
                    y = plot.bottom() - ((value - low) / (high - low) * plot.height())
                    points.append(QPointF(x, y))
                painter.setPen(QPen(QColor("#14b8a6"), 2))
                for left, right in zip(points, points[1:]):
                    painter.drawLine(left, right)

        return _ChartWidget(title)


def _timeframe_combo(combo: Any, current: str) -> Any:
    combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
    combo.setCurrentText(current)
    return combo


def _mt5_candles_for_settings(
    settings: Settings,
    terminal_path: str,
    login: int | None,
    password: str,
    server: str,
) -> list[Candle]:
    gateway = MT5Gateway(
        settings=settings,
        terminal_path=terminal_path,
        login=login,
        password=password,
        server=server,
    )
    symbol = settings.trading.broker_symbol or settings.trading.symbol
    start = _date_start(settings.backtest.start_date)
    end_exclusive = _date_start(settings.backtest.end_date) + timedelta(days=1)
    try:
        gateway.connect()
        candles = gateway.get_candles_range(
            symbol,
            settings.trading.timeframe,
            start,
            end_exclusive,
        )
    except Exception as exc:
        raise RuntimeError(
            "No CSV selected and MT5 historical candles could not be loaded. "
            "Connect MetaTrader 5 or select a candle CSV for the selected symbol. "
            f"MT5 error: {exc}"
        ) from exc
    finally:
        try:
            gateway.disconnect()
        except Exception:
            pass
    if not candles:
        raise RuntimeError(
            f"MT5 returned no candles for {symbol} {settings.trading.timeframe} "
            f"from {settings.backtest.start_date} to {settings.backtest.end_date}."
        )
    return candles


def _date_start(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value))
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=UTC)


def _is_same_symbol_or_empty(broker_symbol: str, symbol: str) -> bool:
    broker = broker_symbol.strip()
    if not broker:
        return True
    return broker.casefold() == symbol.strip().casefold()


def _spin(minimum: int, maximum: int, value: int) -> Any:
    from PySide6.QtWidgets import QSpinBox

    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    return spin


def _double_spin(minimum: float, maximum: float, decimals: int, value: float) -> Any:
    from PySide6.QtWidgets import QDoubleSpinBox

    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setValue(value)
    return spin


def _strategy_text(descriptor: StrategyDescriptor, language: str) -> str:
    parameters = "\n".join(f"- {key}: {value}" for key, value in descriptor.parameters_schema.items())
    if language == "fa":
        return (
            f"{descriptor.name} v{descriptor.version}\n\n"
            f"{descriptor.description}\n\n"
            f"پارامترها\n{parameters}"
        )
    return (
        f"{descriptor.name} v{descriptor.version}\n\n"
        f"{descriptor.description}\n\n"
        f"Parameters\n{parameters}"
    )


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        return f"{value.quantize(Decimal('0.01'))}" if abs(value) >= 10 else f"{value:.5f}"
    return str(value)


def _fmt_indicators(indicators: dict[str, Any]) -> str:
    if not indicators:
        return "-"
    return ", ".join(f"{key}={_fmt(value)}" for key, value in indicators.items())


def _clear_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()

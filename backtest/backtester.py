# backtest/backtester.py
import pandas as pd
from backtesting import Backtest, Strategy
from typing import Dict, Any, Type, Optional, List
import traceback
import os
from datetime import datetime # Import datetime
import math # Import math for isnan check
import numpy as np # Import numpy for nan

# --- Helper Function to Create Logging Strategy Wrapper ---
def create_logging_strategy(
    original_strategy_cls: Type[Strategy],
    order_log: List[Dict[str, Any]],
    offset_value: float = 0.0,         # Renamed
    offset_type: str = 'percent',      # New
    offset_basis: str = 'close'        # New
) -> Type[Strategy]:
    """
    Dynamically creates a new strategy class that wraps the original one
    to log order placement events and apply entry price offset based on type and basis.
    """
    class LoggingStrategyWrapper(original_strategy_cls):
        # Store the shared order log list and offset parameters
        _order_log_list = order_log
        _offset_value = offset_value
        _offset_type = offset_type
        _offset_basis = offset_basis

        def _log_event(self, event_type: str, **kwargs):
            """Helper to add an event to the log."""
            ts = self.data.index[-1] if hasattr(self, 'data') and not self.data.index.empty else datetime.now(tz=datetime.timezone.utc)
            log_entry = {'Timestamp': ts, 'Event': event_type, **kwargs}
            log_entry = {k: v for k, v in log_entry.items() if v is not None and not (isinstance(v, float) and math.isnan(v))}
            self._order_log_list.append(log_entry)
            # print(f"Order Log: {log_entry}") # Uncomment for debug

        def _calculate_offset_price(self, is_buy: bool) -> Optional[float]:
            """Calculates the offset price based on settings."""
            if self._offset_value <= 0:
                return None # No offset applied

            try:
                # Determine basis price
                if self._offset_basis == 'open':
                    # Need to access the *next* bar's open, which isn't directly available in `next()`
                    # This basis is harder to implement correctly in backtesting.py without lookahead bias.
                    # Defaulting to 'close' for now.
                    print(f"Warning: Offset basis 'open' is not reliably implemented, using 'close'.")
                    basis_price = self.data.Close[-1]
                else: # Default to 'close'
                    basis_price = self.data.Close[-1]

                if math.isnan(basis_price):
                    print(f"Warning: Cannot apply offset, basis price ({self._offset_basis}) is NaN at {self.data.index[-1]}")
                    return None

                # Calculate offset amount
                offset_amount = 0.0
                if self._offset_type == 'percent':
                    offset_amount = basis_price * (self._offset_value / 100.0)
                elif self._offset_type == 'atr':
                    # Requires the strategy to have calculated ATR and made it available
                    if hasattr(self, 'atr') and len(self.atr) > 0 and not math.isnan(self.atr[-1]):
                        offset_amount = self.atr[-1] * self._offset_value
                    else:
                        print(f"Warning: Cannot apply ATR offset, 'self.atr' not available or NaN at {self.data.index[-1]}")
                        return None
                else:
                    # Should not happen due to init check, but safeguard
                    return None

                # Apply offset
                if is_buy:
                    calculated_limit = basis_price * (1 - (offset_amount / basis_price) if basis_price != 0 else 0) # Apply slippage against the direction of the trade
                    # calculated_limit = basis_price - offset_amount # Alternative: fixed amount offset
                    print(f"Offset Buy: Basis Price ({self._offset_basis})={basis_price:.4f}, Type={self._offset_type}, Value={self._offset_value}, OffsetAmt={offset_amount:.4f}, Limit Set={calculated_limit:.4f}")
                else: # is_sell
                    calculated_limit = basis_price * (1 + (offset_amount / basis_price) if basis_price != 0 else 0) # Apply slippage against the direction of the trade
                    # calculated_limit = basis_price + offset_amount # Alternative: fixed amount offset
                    print(f"Offset Sell: Basis Price ({self._offset_basis})={basis_price:.4f}, Type={self._offset_type}, Value={self._offset_value}, OffsetAmt={offset_amount:.4f}, Limit Set={calculated_limit:.4f}")

                return calculated_limit

            except IndexError:
                print(f"Warning: Cannot apply offset, not enough data yet (IndexError).")
                return None
            except Exception as e:
                 print(f"Error calculating offset price: {e}")
                 return None


        # --- Override order methods ---
        def buy(self, *, size=.99, limit=None, stop=None, sl=None, tp=None, tag=None):
            calculated_limit = limit # Start with user-provided limit
            original_signal_price = self.data.Close[-1] if hasattr(self.data, 'Close') and len(self.data.Close)>0 else np.nan
            log_details = {'Size': size, 'Limit': limit, 'Stop': stop, 'SL': sl, 'TP': tp, 'Tag': tag, 'OriginalSignalPrice': original_signal_price}

            # Apply offset only if it's intended as a market order (limit and stop are None)
            if limit is None and stop is None:
                offset_price = self._calculate_offset_price(is_buy=True)
                if offset_price is not None:
                    calculated_limit = offset_price
                    log_details['CalculatedLimit (Buy Offset)'] = calculated_limit

            self._log_event('BUY_PLACED', **log_details)

            # Use the calculated_limit if offset was applied, otherwise use original limit/stop
            if calculated_limit is not None and limit is None and stop is None:
                 return super().buy(size=size, limit=calculated_limit, stop=stop, sl=sl, tp=tp, tag=tag)
            else:
                 # Use original parameters if offset not applied or user specified limit/stop
                 return super().buy(size=size, limit=limit, stop=stop, sl=sl, tp=tp, tag=tag)


        def sell(self, *, size=.99, limit=None, stop=None, sl=None, tp=None, tag=None):
            calculated_limit = limit # Start with user-provided limit
            original_signal_price = self.data.Close[-1] if hasattr(self.data, 'Close') and len(self.data.Close)>0 else np.nan
            log_details = {'Size': size, 'Limit': limit, 'Stop': stop, 'SL': sl, 'TP': tp, 'Tag': tag, 'OriginalSignalPrice': original_signal_price}

            # Apply offset only if it's intended as a market order (limit and stop are None)
            if limit is None and stop is None:
                 offset_price = self._calculate_offset_price(is_buy=False)
                 if offset_price is not None:
                     calculated_limit = offset_price
                     log_details['CalculatedLimit (Sell Offset)'] = calculated_limit

            self._log_event('SELL_PLACED', **log_details)

            # Use the calculated_limit if offset was applied, otherwise use original limit/stop
            if calculated_limit is not None and limit is None and stop is None:
                return super().sell(size=size, limit=calculated_limit, stop=stop, sl=sl, tp=tp, tag=tag)
            else:
                # Use original parameters if offset not applied or user specified limit/stop
                return super().sell(size=size, limit=limit, stop=stop, sl=sl, tp=tp, tag=tag)


        def close(self, portion=1.0, tag=None):
            self._log_event('CLOSE_ORDER_PLACED', Portion=portion, Tag=tag)
            super().close(portion=portion, tag=tag)

    # Give the wrapped class a meaningful name
    LoggingStrategyWrapper.__name__ = f"{original_strategy_cls.__name__}_WithLoggingOffset"
    return LoggingStrategyWrapper
# --- End Helper Function ---


class BacktestEngine:
    def __init__(self,
                 data: pd.DataFrame,
                 strategy_class: Type[Strategy],
                 strategy_params: Dict[str, Any],
                 initial_capital: float = 100000,
                 commission: float = 0.002,
                 leverage: float = 1.0,
                 offset_value: float = 0.0,         # Renamed from entry_offset_percent
                 offset_type: str = 'percent',      # New: 'percent' or 'atr'
                 offset_basis: str = 'close'):      # New: 'close' or 'open' (open is tricky)
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data index must be DatetimeIndex.")
        req_cols = ['Open', 'High', 'Low', 'Close']
        if not all(c in data.columns for c in req_cols):
            raise ValueError(f"Data missing required columns: {req_cols}")
        if leverage <= 0:
            print("Warn: Leverage <= 0, setting to 1.0")
            leverage = 1.0
        margin = 1.0 / leverage
        if offset_value < 0:
            print("Warn: Offset Value < 0, setting to 0.0")
            offset_value = 0.0
        if offset_type not in ['percent', 'atr']:
             print(f"Warn: Invalid offset_type '{offset_type}', defaulting to 'percent'.")
             offset_type = 'percent'
        if offset_basis not in ['close', 'open']:
             print(f"Warn: Invalid offset_basis '{offset_basis}', defaulting to 'close'.")
             offset_basis = 'close'
        if offset_type == 'atr':
             print("Info: Offset type 'atr' selected. Ensure the strategy calculates and provides 'ATR' via self.I().")


        self.data = data
        self.strategy_class_original = strategy_class
        self.strategy_params = strategy_params
        self.initial_capital = initial_capital
        self.commission = commission
        # Store new offset parameters
        self.offset_value = offset_value
        self.offset_type = offset_type
        self.offset_basis = offset_basis
        self.order_log: List[Dict[str, Any]] = []

        # --- Wrap the strategy class ---
        self.strategy_class_logged = create_logging_strategy(
            strategy_class,
            self.order_log,
            self.offset_value,
            self.offset_type,
            self.offset_basis
        )
        # --- End Wrapping ---

        print(f"--- BacktestEngine Init ---")
        print(f"  Strategy: {self.strategy_class_logged.__name__} (wrapping {strategy_class.__name__})")
        print(f"  Capital: {initial_capital:,.2f}")
        print(f"  Commission: {commission:.4f}")
        print(f"  Leverage: {leverage:.2f}x")
        print(f"  Margin: {margin:.4f}")
        print(f"  Offset Type: {self.offset_type}")
        print(f"  Offset Basis: {self.offset_basis}")
        print(f"  Offset Value: {self.offset_value:.4f}{'%' if self.offset_type == 'percent' else ' (ATR multiples)'}")
        print(f"  Params: {strategy_params}")
        print(f"--- End Init ---")

        # Store the Backtest instance
        self.bt = Backtest(data, self.strategy_class_logged,
                           cash=self.initial_capital,
                           commission=self.commission,
                           margin=margin,
                           hedging=False,
                           exclusive_orders=True)
        self.stats: Optional[pd.Series] = None

    def run(self) -> None:
        print("BacktestEngine: Running self.bt.run()...")
        self.order_log.clear()
        try:
            self.stats = self.bt.run(**self.strategy_params)
            print("BacktestEngine: self.bt.run() finished.")
        except Exception as e:
            print(f"BacktestEngine: Exception during run: {e}")
            traceback.print_exc()
            raise

    def get_analysis_results(self) -> Dict[str, Any]:
        """
        Analyzes the backtest results and returns a dictionary containing
        performance metrics, equity curve, trades, order log, and execution log.
        """
        print("BacktestEngine: Generating analysis results...")
        execution_log = [] # Initialize execution log

        if self.stats is None:
            print("Warning: Backtest run might not have completed successfully or produced stats.")
            # Return empty metrics but include logs if any
            return {
                'performance_metrics': {},
                'equity_curve': pd.DataFrame(),
                'trades': pd.DataFrame(),
                '_order_log': self.order_log,
                '_execution_log': execution_log # Return empty execution log
            }

        s = self.stats
        # Extract standard metrics
        metrics = {k: s.get(k) for k in ['Start', 'End', 'Duration', 'Equity Final [$]', 'Equity Peak [$]', 'Return [%]', 'Buy & Hold Return [%]', 'Return (Ann.) [%]', 'Volatility (Ann.) [%]', 'Sharpe Ratio', 'Sortino Ratio', 'Calmar Ratio', 'Max. Drawdown [%]', 'Avg. Drawdown [%]', 'Max. Drawdown Duration', 'Avg. Drawdown Duration', '# Trades', 'Win Rate [%]', 'Best Trade [%]', 'Worst Trade [%]', 'Avg. Trade [%]', 'Max. Trade Duration', 'Avg. Trade Duration', 'Profit Factor', 'Expectancy [%]', 'SQN']}
        fm = {k: v for k, v in metrics.items() if v is not None and not (isinstance(v, float) and pd.isna(v))}

        # --- Process Trades DataFrame into Execution Log ---
        trades_df = getattr(s, '_trades', pd.DataFrame())
        if not trades_df.empty:
            # Convert trades DataFrame rows into a list of dictionaries (log format)
            # Rename columns for clarity if needed
            trades_df_renamed = trades_df.rename(columns={
                'Size': 'ExecutedSize',
                'EntryTime': 'EntryTimestamp',
                'ExitTime': 'ExitTimestamp',
                'EntryPrice': 'EntryExecPrice',
                'ExitPrice': 'ExitExecPrice',
                'PnL': 'ProfitLoss',
                'ReturnPct': 'ReturnPercent',
                'EntryBar': 'EntryBarIndex',
                'ExitBar': 'ExitBarIndex',
                'Duration': 'TradeDurationBars'
                # Keep 'SlPrice', 'TpPrice', 'Commission', 'Tag' if they exist
            })
            # Convert Timestamp columns to appropriate format if needed (they should be datetime already)
            # Select relevant columns for the log
            log_columns = ['ExecutedSize', 'EntryTimestamp', 'ExitTimestamp', 'EntryExecPrice', 'ExitExecPrice', 'ProfitLoss', 'ReturnPercent', 'Commission', 'Tag']
            # Filter columns that actually exist in the renamed DataFrame
            existing_log_columns = [col for col in log_columns if col in trades_df_renamed.columns]
            # Convert DataFrame to list of dicts, handling potential NaT/NaN values during conversion
            execution_log_raw = trades_df_renamed[existing_log_columns].to_dict('records')
            execution_log = []
            for entry_raw in execution_log_raw:
                 entry = {'Event': 'TRADE_EXECUTED'}
                 for k, v in entry_raw.items():
                      # Explicitly check for Pandas NaT or float NaN
                      if pd.isna(v):
                           entry[k] = None # Represent missing values as None in the log
                      else:
                           entry[k] = v
                 execution_log.append(entry)


        # Prepare the final results dictionary
        results = {
            'performance_metrics': fm,
            'equity_curve': getattr(s, '_equity_curve', pd.DataFrame()),
            'trades': trades_df, # Return original trades DataFrame as well
            '_order_log': self.order_log,
            '_execution_log': execution_log # Add the processed execution log
        }

        print("BacktestEngine: Analysis results generated.")
        return results

    def generate_plot(self, filename="_backtest_plot.html", plot_trades=True) -> Optional[str]:
        if self.bt is None or self.stats is None:
            print("Error: Backtest has not been run successfully. Cannot generate plot.")
            return None
        print(f"BacktestEngine: Generating plot file '{filename}'...")
        try:
            output_dir = os.path.dirname(filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            self.bt.plot(filename=filename, open_browser=False, plot_trades=plot_trades)
            abs_path = os.path.abspath(filename)
            print(f"BacktestEngine: Plot saved successfully to {abs_path}")
            return abs_path
        except Exception as e:
            print(f"BacktestEngine: Error generating plot: {e}")
            traceback.print_exc()
            return None

    def optimize(self, **kwargs) -> pd.Series:
         print(f"BacktestEngine: Optimizing with {kwargs}")
         if 'maximize' not in kwargs: kwargs['maximize'] = 'Sharpe Ratio'
         print("Warning: Optimization uses the original strategy class. Logging and offset are not active during optimization.")
         bt_optimize = Backtest(self.data, self.strategy_class_original,
                                cash=self.initial_capital, commission=self.commission,
                                margin=(1.0 / kwargs.get('leverage', 1.0)),
                                hedging=False, exclusive_orders=True)
         try:
             opt_results = bt_optimize.optimize(**kwargs)
             print("BacktestEngine: Optimization finished.")
             return opt_results
         except Exception as e:
             print(f"BacktestEngine: Optimization error: {e}")
             traceback.print_exc()
             raise

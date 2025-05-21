# utils/strategy_loader.py

import os
import importlib
import inspect
import sys
import traceback

# Import Strategy base class for type checking
try:
    from backtesting import Strategy as BacktestingStrategy
except ImportError:
    print("Warning (strategy_loader): backtesting library not found. Strategy type check relies on object.")
    BacktestingStrategy = object # Fallback

def filename_to_classname(filename):
    """Converts a snake_case filename to PascalCaseStrategyName."""
    base_name = filename[:-3] # Remove .py
    parts = base_name.split('_')
    class_name = "".join(part.capitalize() for part in parts) + "Strategy"
    return class_name

def load_available_strategies(strategies_path='./strategies'):
    """
    Scans the specified directory for valid strategy files and classes.

    Args:
        strategies_path (str): The path to the strategies directory.

    Returns:
        dict: A dictionary mapping display names to strategy classes.
              Returns an empty dictionary if the path is invalid, no __init__.py
              is found, or no valid strategies are discovered.
    """
    strategy_classes = {}
    strategy_display_names = [] # Keep track for sorting later if needed by caller

    # --- Basic Checks ---
    init_path = os.path.join(strategies_path, '__init__.py')
    if not os.path.isdir(strategies_path):
        print(f"策略文件夾 '{strategies_path}' 不存在。")
        return {}
    if not os.path.exists(init_path):
        print(f"策略文件夾 '{strategies_path}' 中缺少 '__init__.py' 文件。")
        return {}
    # Check if __init__.py is empty (recommended)
    try:
        if os.path.getsize(init_path) > 0:
            print(f"警告: '{init_path}' 文件不是空的，可能導致意外導入行為。")
    except OSError as e:
        print(f"警告: 無法檢查 '{init_path}' 文件大小: {e}")

    print(f"開始從 '{strategies_path}' 加載策略...")
    # --- Ensure package is known ---
    # Get the package name from the path (e.g., './strategies' -> 'strategies')
    package_name = os.path.basename(strategies_path)
    if package_name not in sys.modules:
        try:
            # Attempt to import the package itself first
            importlib.import_module(package_name)
            print(f"  已將包 '{package_name}' 加入 sys.modules。")
        except ImportError as e:
             print(f"  警告：無法將包 '{package_name}' 作為頂級模塊導入: {e}")
             print(f"  將嘗試直接導入子模塊...")
             # If it fails, proceed to import submodules directly, might still work depending on context

    # --- Scan and Import ---
    for filename in os.listdir(strategies_path):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            # Assuming 'strategies' is the package name relative to the project root
            module_path = f"{package_name}.{module_name}"
            print(f"  嘗試導入模塊: {module_path}")
            try:
                # --- Use reload for development, import_module for production ---
                # For simplicity here, let's use import_module which caches
                # If you need live reloading during development, add the reload logic back carefully
                if module_path in sys.modules:
                    strategy_module = importlib.reload(sys.modules[module_path])
                    print(f"    重新加載: {module_path}")
                else:
                     strategy_module = importlib.import_module(module_path)

                # --- Find Strategy Class ---
                found_class = None
                for name, obj in inspect.getmembers(strategy_module):
                    # Check: Is it a class? Defined in *this* module? Inherits Strategy? Not Strategy itself?
                    if inspect.isclass(obj) and \
                       obj.__module__ == module_path and \
                       issubclass(obj, BacktestingStrategy) and \
                       obj is not BacktestingStrategy:
                        found_class = obj
                        print(f"    找到策略類: {name}")
                        break # Assume one strategy per file

                if found_class:
                    # Generate display name (e.g., "Macd Divergence")
                    display_name = ' '.join(word.capitalize() for word in module_name.split('_'))
                    strategy_classes[display_name] = found_class
                    strategy_display_names.append(display_name) # Keep track if needed
                else:
                    print(f"    警告: 在 {filename} 中未找到繼承自 Strategy 的有效策略類。")

            except ImportError as ie:
                # Errors importing *within* the strategy file
                print(f"警告: 導入 {module_name} 時發生內部導入錯誤: {ie}")
                print(f"      (請檢查 '{filename}' 文件內的導入語句)")
            except Exception as e:
                # Other errors during import or inspection
                print(f"警告: 加載策略 {module_name} 時發生錯誤: {e}")
                traceback.print_exc(limit=1) # Print limited traceback

    print(f"策略加載完成。找到 {len(strategy_classes)} 個有效策略。")
    return strategy_classes
# main.py (Lean Entry Point)

import tkinter as tk
import os
import traceback       # <<< --- 添加導入 traceback
from tkinter import messagebox # <<<--- 添加導入 messagebox

# --- Optional: Use ttkthemes for better styling ---
USE_THEMES = False # Set to True to try themes (requires pip install ttkthemes)
DEFAULT_THEME = "arc" # Example theme: arc, clam, adapta, etc.

# --- Import the main GUI application class ---
try:
    # Assuming gui/app.py contains the TradingAppGUI class (renamed from BacktestGUI)
    from gui.app import TradingAppGUI
    # 可能需要添加Google API客戶端庫
    import google.cloud.aiplatform as aiplatform
except ImportError as e:
    print(f"無法導入必要組件: {e}")
    print("請確保 gui 文件夾和 gui/app.py 文件存在，並且所有依賴項已安裝。")
    # Try showing an error box if messagebox was imported
    try:
        messagebox.showerror("啟動錯誤", f"無法導入 GUI 組件: {e}\n請檢查文件結構和依賴項。")
    except NameError:
        print("Messagebox not available for error display.") # Fallback if import failed early
    input("按 Enter 鍵退出...") # Pause for user to see the message
    exit(1)

# --- Helper to ensure directory exists (basic version for main) ---
def ensure_dir(path):
    if not os.path.isdir(path):
        print(f"文件夾 '{path}' 不存在，正在創建...")
        try:
            os.makedirs(path)
        except OSError as e:
            print(f"錯誤：無法創建文件夾 '{path}': {e}")
            return False
    return True

# --- Main execution block ---
if __name__ == "__main__":
    print("正在啟動回測系統...")

    # --- Ensure essential directories exist before starting GUI ---
    required_dirs = ['./data', './strategies']
    for d in required_dirs:
        if not ensure_dir(d):
            print(f"無法啟動，因為必需的文件夾 '{d}' 無法創建。")
            input("按 Enter 鍵退出...")
            exit(1)
        # Ensure __init__.py exists in strategies (GUI's loader handles details)
        init_path = os.path.join('./strategies', '__init__.py')
        if d == './strategies' and not os.path.exists(init_path):
             try:
                 print(f"'{init_path}' 不存在，正在創建空文件...")
                 with open(init_path, 'w') as f: f.write("")
                 print(f"已創建空的 '{init_path}'。")
             except OSError as e:
                 print(f"警告：無法自動創建 '{init_path}': {e}")
                 # Don't exit, but loading might fail later

    # --- Initialize Tkinter root window ---
    root = None
    if USE_THEMES:
        try:
            from ttkthemes import ThemedTk
            print(f"嘗試使用 ttkthemes 主題: '{DEFAULT_THEME}'...")
            root = ThemedTk(theme=DEFAULT_THEME)
        except ImportError:
            print("ttkthemes 未安裝，將使用默認 Tk 主題。 (pip install ttkthemes)")
            root = tk.Tk()
        except tk.TclError:
             print(f"主題 '{DEFAULT_THEME}' 加載失敗，使用默認 Tk 主題。")
             root = tk.Tk()
    else:
        print("使用標準 Tk 主題。")
        root = tk.Tk()

    # --- Create and run the GUI application ---
    try:
        print("正在初始化 GUI...")
        app = TradingAppGUI(root) # Create instance of the GUI class from gui.app
        print("啟動 Tkinter mainloop...")
        root.mainloop() # Start the Tkinter event loop
        print("程序已退出。")
    except Exception as e:
        # Catch potential errors during GUI initialization or runtime
        print("\n--- GUI 運行時發生嚴重錯誤 ---")
        # Now traceback and messagebox should be defined
        traceback.print_exc() # Print the full traceback to console
        try:
             # Use the imported messagebox
             messagebox.showerror("嚴重錯誤", f"GUI 運行時發生錯誤:\n{e}\n\n詳情請查看控制台。")
        except tk.TclError: # Catch errors if Tkinter itself is broken
             print("無法顯示錯誤彈窗 (Tkinter 可能已損壞)。")
        except Exception as msg_e: # Catch other potential messagebox errors
             print(f"嘗試顯示錯誤彈窗時發生額外錯誤: {msg_e}")
        input("按 Enter 鍵退出...")
        exit(1)

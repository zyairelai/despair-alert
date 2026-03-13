import os, sys, subprocess, shutil

# Get the absolute path of the directory where despair.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_LIST = [
    ("ema_single.py",  "EMA 10/20 Cross Single Timeframe"),
    ("ema_double.py",  "EMA 10/20/50 Alignment (15m + 5m)"),
    ("heikin.py",      "Heikin Ashi Color Change"),
    ("hourbreak.py",   "1H Structure Break"),
    ("linetouch.py",   "Check Specific Price Touch"),
    ("monitoring.py",  "Live Trend Dashboard"),
    ("oneminute.py",   "One Minute Entry Alert"),
    ("pricealert.py",  "Custom Price Alert"),
    ("standing.py",    "Close Above/Below MA Check"),
    ("stoploss.py",    "Stoploss Multi-Price Alert"),
    ("zones.py",       "Prev 1D/4H Levels")
]

# Sort alphabetically by filename (the first element of each tuple)
SCRIPTS_LIST.sort(key=lambda x: x[0])

def clear_pycache():
    """Delete all __pycache__ folders in the project directory and subdirectories."""
    count = 0
    for root, dirs, _ in os.walk(SCRIPT_DIR):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(pycache_path)
                count += 1
            except Exception as e: print(f"[!] Error cleaning {pycache_path}: {e}")
    if count > 0: print(f"[i] Cleaned up {count} __pycache__ folder(s).")

def display_menu(sorted_scripts):
    print("\n========================= SCRIPTS =========================")
    for idx, (script, desc) in enumerate(sorted_scripts, start=1):
        print(f"{idx:>2}. {script:<13} -  {desc}")
    print("==========================================================")

def main():
    try:
        display_menu(SCRIPTS_LIST)
        user_input = input("\nEnter Script: ").strip()
        if not user_input: return

        parts = user_input.split()
        try:
            choice_idx = int(parts[0]) - 1
            args = parts[1:]
        except ValueError:
            print(f"[!] Invalid input: {parts[0]} is not a number.")
            return

        if 0 <= choice_idx < len(SCRIPTS_LIST):
            script_name, _ = SCRIPTS_LIST[choice_idx]
            script_path = os.path.join(SCRIPT_DIR, script_name)
            
            # Use subprocess.run with a list to prevent shell injection
            cmd = [sys.executable, script_path] + args
            
            print(f"\n[+] Running: {' '.join(cmd)}")
            try: subprocess.run(cmd)
            except KeyboardInterrupt: print("\n[!] Script execution interrupted.")
        else: print(f"[!] Invalid choice number: {choice_idx + 1}")

    except KeyboardInterrupt: print("\n\nAborted.")
    except Exception as e: print(f"[!] Unexpected error: {e}")
    finally: clear_pycache()

if __name__ == "__main__":
    main()
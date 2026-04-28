#!/usr/bin/python3
import os, sys, subprocess, shutil

# Get the absolute path of the directory where despair.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_LIST = [
    ("complicated.py",  "Double TF Structure Break"),
    ("flask.py",        "Telegram Webhook Bot"),
    ("hourbreak.py",    "1H Structure Break & Pin Bar"),
    ("monitoring.py",   "Live Trend & 1H Emergency"),
    ("okx.py",          "OKX Exchange Monitoring"),
    ("oneminute.py",    "1m/5m Scalping Alerts"),
    ("pricealert.py",   "Multi-Target Price Alerts"),
    ("zones.py",        "Prev 1D/4H Levels")
]

# Sort alphabetically by filename
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
        print(f"{idx:>2}. {script:<15}  -  {desc}")
    print("==========================================================")

def main():
    try:
        display_menu(SCRIPTS_LIST)
        user_input = input("\nEnter Script Number or Name: ").strip()

        if not user_input:
            script_name = "monitoring.py"
            args = []
        else:
            parts = user_input.split()
            choice = parts[0].lower()
            args = parts[1:]
            script_name = None
            # Simple numeric or exact name matching
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(SCRIPTS_LIST):
                    script_name, _ = SCRIPTS_LIST[choice_idx]
            except ValueError:
                # Check if exact filename was typed
                if choice.endswith(".py"):
                    script_name = choice
                elif os.path.exists(os.path.join(SCRIPT_DIR, choice + ".py")):
                    script_name = choice + ".py"

        if script_name:
            script_path = os.path.join(SCRIPT_DIR, script_name)
            if not os.path.exists(script_path):
                print(f"[!] Error: {script_name} not found.")
                return

            cmd = [sys.executable, script_path] + args
            print(f"\n[+] Running: {' '.join(cmd)}")
            try: subprocess.run(cmd)
            except KeyboardInterrupt: print("\n[!] Script execution interrupted.")
        else:
            print("[!] Invalid selection.")

    except KeyboardInterrupt: print("\n\nAborted.")
    except Exception as e: print(f"[!] Unexpected error: {e}")
    finally: clear_pycache()

if __name__ == "__main__":
    main()

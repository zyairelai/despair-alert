#!/usr/bin/python3
import os, sys, subprocess, shutil

# Get the absolute path of the directory where despair.py is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPTS_LIST = [
    ("hourbreak.py",   "1H Structure Break"),
    ("monitoring.py",  "Live Trend Dashboard"),
    ("oneminute.py",   "One Minute Entry Alert"),
    ("rawcandle.py",   "5m Long Upper Wick Monitoring"),
    ("zones.py",       "Prev 1D/4H Levels")
]

# Sort alphabetically by filename (the first element of each tuple)
SCRIPTS_LIST.sort(key=lambda x: x[0])

SHORTCUTS = {
    "h": "hourbreak.py",
    "m": "monitoring.py",
    "o": "oneminute.py",
    "r": "rawcandle.py",
    "z": "zones.py"
}

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
    shortcut_rev = {v: k for k, v in SHORTCUTS.items()}
    for idx, (script, desc) in enumerate(sorted_scripts, start=1):
        sc = shortcut_rev.get(script, "")
        sc_label = f"({sc})" if sc else "   "
        print(f"{idx:>2}. {script:<13} {sc_label}  -  {desc}")
    print("==========================================================")

def main():
    try:
        display_menu(SCRIPTS_LIST)
        user_input = input("\nEnter Script: ").strip()
        
        if not user_input:
            script_name = "monitoring.py"
            args = []
        else:
            parts = user_input.split()
            choice = parts[0].lower()
            args = parts[1:]
            
            script_name = None
            
            if choice in SHORTCUTS:
                script_name = SHORTCUTS[choice]
            elif choice in ['0', '00']:
                script_name = "monitoring.py"
            else:
                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(SCRIPTS_LIST):
                        script_name, _ = SCRIPTS_LIST[choice_idx]
                    else:
                        script_name = "monitoring.py"
                except ValueError:
                    script_name = "monitoring.py"

        if script_name:
            script_path = os.path.join(SCRIPT_DIR, script_name)
            cmd = [sys.executable, script_path] + args
            
            print(f"\n[+] Running: {' '.join(cmd)}")
            try: subprocess.run(cmd)
            except KeyboardInterrupt: print("\n[!] Script execution interrupted.")

    except KeyboardInterrupt: print("\n\nAborted.")
    except Exception as e: print(f"[!] Unexpected error: {e}")
    finally: clear_pycache()

if __name__ == "__main__":
    main()

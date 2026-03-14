#!/usr/bin/env python3
"""
CrowdStrike Falcon FlightControl Toolkit - Main Launcher

This launcher provides a centralized menu to access all toolkit scripts.
After each script execution, you'll return to this menu.

Author: Claude Opus 4.6
Date: 2026-03-14
"""

import sys
import os
import subprocess
import random
import time
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from utils.formatting import print_jg_logo, print_header, print_section, print_info, print_success, print_error, Colors

# Script definitions
SCRIPTS = {
    'firewall': {
        'name': 'Firewall Management Replicator',
        'description': 'Replicate firewall policies, rule groups, and network locations',
        'path': 'script_replicate_firewall/replicate_firewall.py',
        'category': 'Replication',
        'icon': '🛡️',
        'color': Colors.SUCCESS,
        'badge': '⭐',
        'shortcut': 'f'
    },
    'ioas': {
        'name': 'Custom IOAs Replicator',
        'description': 'Replicate Custom IOA rules to Child CIDs',
        'path': 'script_replicate_custom_ioas/replicate_custom_ioas.py',
        'category': 'Replication',
        'icon': '🎯',
        'color': Colors.SUCCESS,
        'badge': '⚡',
        'shortcut': 'i'
    },
    'roles': {
        'name': 'Custom Roles Analyzer',
        'description': 'Analyze and document custom roles across CIDs',
        'path': 'script_analyze_roles/analyze_roles.py',
        'category': 'Analysis',
        'icon': '🔍',
        'color': Colors.INFO,
        'badge': '📋',
        'shortcut': 'r'
    },
    'export': {
        'name': 'Devices & Policies Exporter',
        'description': 'Export device and policy data to CSV/Excel',
        'path': 'script_export_devices_policies/export_devices_policies.py',
        'category': 'Export',
        'icon': '📊',
        'color': Colors.HIGHLIGHT,
        'badge': '💾',
        'shortcut': 'e'
    }
}

# Session stats
session_stats = {
    'scripts_run': 0,
    'successes': 0,
    'errors': 0,
    'start_time': datetime.now(),
    'last_script': None
}

# Tips to display randomly
TIPS = [
    "Use Ctrl+C anytime to return safely",
    "All scripts support interactive and non-interactive modes",
    "Check logs/ directory for detailed execution logs",
    "Credentials can be set via environment variables",
    "Use --help flag with any script for options",
    "Always test in non-production first"
]


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_session_duration():
    """Get formatted session duration"""
    duration = datetime.now() - session_stats['start_time']
    minutes = int(duration.total_seconds() / 60)
    if minutes < 1:
        return "< 1 min"
    elif minutes == 1:
        return "1 min"
    else:
        return f"{minutes} mins"


def display_menu():
    """Display the main menu"""
    clear_screen()
    print_jg_logo()

    # ASCII art title
    print(f"  {Colors.HIGHLIGHT}{'━' * 78}{Colors.RESET}")
    print()
    print(f"   {Colors.SUCCESS}██████╗ ███████╗{Colors.RESET}    {Colors.HIGHLIGHT}███████╗ █████╗ ██╗      ██████╗ ██████╗ ███╗   ██╗{Colors.RESET}")
    print(f"  {Colors.SUCCESS}██╔════╝ ██╔════╝{Colors.RESET}    {Colors.HIGHLIGHT}██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗████╗  ██║{Colors.RESET}")
    print(f"  {Colors.SUCCESS}██║      ███████╗{Colors.RESET}    {Colors.HIGHLIGHT}█████╗  ███████║██║     ██║     ██║   ██║██╔██╗ ██║{Colors.RESET}")
    print(f"  {Colors.SUCCESS}██║      ╚════██║{Colors.RESET}    {Colors.HIGHLIGHT}██╔══╝  ██╔══██║██║     ██║     ██║   ██║██║╚██╗██║{Colors.RESET}")
    print(f"  {Colors.SUCCESS}╚██████╗ ███████║{Colors.RESET}    {Colors.HIGHLIGHT}██║     ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║{Colors.RESET}")
    print(f"   {Colors.SUCCESS}╚═════╝ ╚══════╝{Colors.RESET}    {Colors.HIGHLIGHT}╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝{Colors.RESET}")
    print()
    print(f"         {Colors.INFO}🦅 F L I G H T C O N T R O L   T O O L K I T{Colors.RESET}")
    print()
    print(f"  {Colors.HIGHLIGHT}{'━' * 78}{Colors.RESET}")
    print()

    # Mini status bar
    duration = get_session_duration()
    success_rate = "N/A"
    if session_stats['scripts_run'] > 0:
        rate = (session_stats['successes'] / session_stats['scripts_run']) * 100
        success_rate = f"{rate:.0f}%"

    print(f"  {Colors.DIM}⏱ {duration}  │  📊 {session_stats['scripts_run']} runs  │  ✓ {success_rate}  │  💡 {random.choice(TIPS)}{Colors.RESET}")
    print()

    # Group scripts by category
    categories = {}
    for key, script in SCRIPTS.items():
        category = script['category']
        if category not in categories:
            categories[category] = []
        categories[category].append((key, script))

    # Display scripts by category
    idx = 1
    menu_mapping = {}

    # Category styles
    category_styles = {
        'Replication': {'emoji': '🔄', 'color': Colors.SUCCESS},
        'Analysis': {'emoji': '📈', 'color': Colors.INFO},
        'Export': {'emoji': '💾', 'color': Colors.HIGHLIGHT}
    }

    for category in ['Replication', 'Analysis', 'Export']:
        if category in categories:
            style = category_styles.get(category, {'emoji': '📂', 'color': Colors.RESET})
            count = len(categories[category])

            # Compact category header with count
            print(f"  {style['color']}{style['emoji']}  {category.upper()} ({count}){Colors.RESET}")
            print(f"  {Colors.DIM}{'─' * 78}{Colors.RESET}")

            for key, script in categories[category]:
                badge = script.get('badge', '')
                shortcut = script.get('shortcut', '').upper()

                # Check if this was the last executed script
                last_indicator = ' ★' if session_stats['last_script'] == key else ''

                # Compact button with colored number and shortcut
                print(f"  {script['color']}┌{'─' * 76}┐{Colors.RESET}")
                print(f"  {script['color']}│{Colors.RESET} {script['icon']} {script['color']}[{idx}/{shortcut}]{Colors.RESET} {script['name']} {Colors.DIM}{badge}{last_indicator}{Colors.RESET}" + " " * (61 - len(script['name']) - len(badge) - len(last_indicator)) + f"{script['color']}│{Colors.RESET}")
                print(f"  {script['color']}│{Colors.RESET} {Colors.DIM}   {script['description']}{Colors.RESET}" + " " * (72 - len(script['description'])) + f"{script['color']}│{Colors.RESET}")
                print(f"  {script['color']}└{'─' * 76}┘{Colors.RESET}")
                print()
                menu_mapping[idx] = key
                menu_mapping[shortcut.lower()] = key  # Add shortcut mapping
                idx += 1

    # Compact quit button
    print(f"  {Colors.ERROR}┌{'─' * 76}┐{Colors.RESET}")
    print(f"  {Colors.ERROR}│{Colors.RESET} ❌ {Colors.ERROR}[Q]{Colors.RESET} Quit  {Colors.DIM}│{Colors.RESET}  Press Ctrl+C for quick exit" + " " * 41 + f"{Colors.ERROR}│{Colors.RESET}")
    print(f"  {Colors.ERROR}└{'─' * 76}┘{Colors.RESET}")
    print()

    # Mini help
    print(f"  {Colors.DIM}💡 Pro tip: Type a number (1-4), first letter (F/I/R/E), or Q to quit{Colors.RESET}")
    print()

    return menu_mapping


def run_script(script_path: str) -> bool:
    """Run a script and return True if successful"""
    script_full_path = Path(__file__).parent / script_path

    if not script_full_path.exists():
        print_error(f"Script not found: {script_path}")
        return False

    session_stats['scripts_run'] += 1

    try:
        result = subprocess.run(
            [sys.executable, str(script_full_path)],
            cwd=script_full_path.parent
        )

        print()

        if result.returncode == 0:
            session_stats['successes'] += 1
        else:
            session_stats['errors'] += 1

        return result.returncode == 0

    except KeyboardInterrupt:
        print()
        session_stats['errors'] += 1
        print_error("✗ Script interrupted by user")
        return False
    except Exception as e:
        print()
        session_stats['errors'] += 1
        print_error(f"✗ Error running script: {e}")
        return False


def wait_for_keypress():
    """Wait for user to press Enter"""
    print()
    print(f"  {Colors.DIM}{'─' * 78}{Colors.RESET}")
    input(f"  {Colors.INFO}Press Enter to return to menu...{Colors.RESET} ")


def show_goodbye_screen():
    """Display goodbye screen with session summary"""
    clear_screen()
    print()
    print(f"  {Colors.SUCCESS}{'━' * 78}{Colors.RESET}")
    print(f"  {Colors.SUCCESS}  🚀 Thank you for using the FlightControl Toolkit!{Colors.RESET}")
    print(f"  {Colors.SUCCESS}{'━' * 78}{Colors.RESET}")
    print()

    # Session summary
    duration = get_session_duration()
    print(f"  {Colors.INFO}SESSION SUMMARY{Colors.RESET}")
    print(f"  {Colors.DIM}{'─' * 78}{Colors.RESET}")
    print(f"  Duration: {duration}  │  Scripts run: {session_stats['scripts_run']}  │  Successful: {Colors.SUCCESS}{session_stats['successes']}{Colors.RESET}  │  Errors: {Colors.ERROR}{session_stats['errors']}{Colors.RESET}")
    print()
    print(f"  {Colors.DIM}Made with ❤️  by the community  │  github.com/haysjg{Colors.RESET}")
    print()


def main():
    """Main launcher loop"""

    while True:
        menu_mapping = display_menu()

        try:
            choice = input(f"  {Colors.HIGHLIGHT}▶ Select (1-4, F/I/R/E, or Q):{Colors.RESET} ").strip().lower()

            if choice == 'q':
                show_goodbye_screen()
                break

            # Check if valid choice (number or letter)
            script_key = None
            if choice.isdigit():
                choice_num = int(choice)
                if choice_num in menu_mapping:
                    script_key = menu_mapping[choice_num]
            elif choice in menu_mapping:
                script_key = menu_mapping[choice]

            if script_key:
                script_info = SCRIPTS[script_key]

                # Launch message
                print()
                print(f"  {script_info['color']}━━━ {script_info['icon']}  Launching: {script_info['name']} {'━' * (45 - len(script_info['name']))}{Colors.RESET}")
                print()

                # Progress bar animation
                print(f"  {Colors.DIM}[", end='', flush=True)
                for i in range(10):
                    time.sleep(0.08)
                    print("█", end='', flush=True)
                print(f"]{Colors.RESET}\n")

                success = run_script(script_info['path'])

                # Update last script
                session_stats['last_script'] = script_key

                # Result
                print()
                if success:
                    print(f"  {Colors.SUCCESS}✓ Script completed successfully!{Colors.RESET}")
                else:
                    print(f"  {Colors.ERROR}✗ Script encountered an error (check logs/){Colors.RESET}")

                wait_for_keypress()
            else:
                print(f"  {Colors.ERROR}✗ Invalid selection - Try 1-4, F/I/R/E, or Q{Colors.RESET}")
                time.sleep(1.2)

        except KeyboardInterrupt:
            show_goodbye_screen()
            break
        except EOFError:
            print()
            break


if __name__ == "__main__":
    main()

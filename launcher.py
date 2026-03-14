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
from pathlib import Path

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
        'name': 'Firewall Management Replication',
        'description': 'Replicate firewall policies, rule groups, and network locations',
        'path': 'script_replicate_firewall/replicate_firewall.py',
        'category': 'Replication'
    },
    'ioas': {
        'name': 'Custom IOAs Replication',
        'description': 'Replicate Custom IOA rules to Child CIDs',
        'path': 'script_replicate_custom_ioas/replicate_custom_ioas.py',
        'category': 'Replication'
    },
    'roles': {
        'name': 'Analyze Custom Roles',
        'description': 'Analyze and document custom roles across CIDs',
        'path': 'script_analyze_roles/analyze_roles.py',
        'category': 'Analysis'
    },
    'export': {
        'name': 'Export Devices & Policies',
        'description': 'Export device and policy data to CSV/Excel',
        'path': 'script_export_devices_policies/export_devices_policies.py',
        'category': 'Export'
    },
    'generate_test': {
        'name': 'Generate Firewall Test Data',
        'description': 'Create test data for firewall replication testing',
        'path': 'tooling/generate_firewall_test_data.py',
        'category': 'Testing'
    },
    'cleanup_test': {
        'name': 'Cleanup Firewall Test Data',
        'description': 'Remove test data from Child CIDs',
        'path': 'tooling/cleanup_test_data.py',
        'category': 'Testing'
    },
    'check_data': {
        'name': 'Check Current Firewall Data',
        'description': 'View current firewall configuration status',
        'path': 'tooling/check_current_data.py',
        'category': 'Utility'
    }
}


def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def display_menu():
    """Display the main menu"""
    clear_screen()
    print_jg_logo()
    print_header("CROWDSTRIKE FALCON FLIGHTCONTROL TOOLKIT")
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

    for category in ['Replication', 'Analysis', 'Export', 'Testing', 'Utility']:
        if category in categories:
            print_section(f"{category} Scripts", char="─", width=80)
            for key, script in categories[category]:
                print(f"  [{idx}] {script['name']}")
                print(f"      {Colors.DIM}{script['description']}{Colors.RESET}")
                print()
                menu_mapping[idx] = key
                idx += 1

    print_section("Options", char="─", width=80)
    print(f"  [q] Quit")
    print()

    return menu_mapping


def run_script(script_path: str) -> bool:
    """Run a script and return True if successful

    Args:
        script_path: Path to the script to run

    Returns:
        True if script executed successfully, False otherwise
    """
    script_full_path = Path(__file__).parent / script_path

    if not script_full_path.exists():
        print_error(f"Script not found: {script_path}")
        return False

    print_info(f"Launching: {script_path}")
    print()

    try:
        # Run script in the same Python environment
        result = subprocess.run(
            [sys.executable, str(script_full_path)],
            cwd=script_full_path.parent
        )

        print()
        if result.returncode == 0:
            print_success("✓ Script completed successfully")
        else:
            print_error(f"✗ Script exited with code {result.returncode}")

        return result.returncode == 0

    except KeyboardInterrupt:
        print()
        print_error("✗ Script interrupted by user")
        return False
    except Exception as e:
        print()
        print_error(f"✗ Error running script: {e}")
        return False


def wait_for_keypress():
    """Wait for user to press Enter"""
    print()
    input(f"{Colors.INFO}Press Enter to return to menu...{Colors.RESET}")


def main():
    """Main launcher loop"""

    while True:
        menu_mapping = display_menu()

        try:
            choice = input(f"{Colors.HIGHLIGHT}Select an option: {Colors.RESET}").strip().lower()

            if choice == 'q':
                print()
                print_success("Thank you for using the FlightControl Toolkit! 🚀")
                print()
                break

            try:
                choice_num = int(choice)
                if choice_num in menu_mapping:
                    script_key = menu_mapping[choice_num]
                    script_info = SCRIPTS[script_key]

                    print()
                    print_section(f"Running: {script_info['name']}")
                    print()

                    run_script(script_info['path'])
                    wait_for_keypress()
                else:
                    print_error("Invalid selection. Please try again.")
                    wait_for_keypress()
            except ValueError:
                print_error("Invalid input. Please enter a number or 'q' to quit.")
                wait_for_keypress()

        except KeyboardInterrupt:
            print()
            print()
            print_success("Thank you for using the FlightControl Toolkit! 🚀")
            print()
            break
        except EOFError:
            print()
            break


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Replicate Custom IOAs from Parent CID to Child CIDs in Flight Control.

This script:
1. Lists all Custom IOAs in the Parent CID
2. Allows interactive selection of IOAs to replicate
3. Allows selection of target Child CIDs
4. Optionally applies replicated IOAs to all prevention policies in Child CIDs
5. Creates the IOAs and links them to policies

Usage:
    python replicate_custom_ioas.py --config config/credentials.json
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from falconpy import CustomIOA, FlightControl, PreventionPolicy
from utils.auth import get_credentials_smart
from utils.common import check_response, extract_resources
from utils.formatting import (
    print_header, print_success, print_error, print_info, print_warning,
    print_progress, print_summary_box, print_section, print_jg_logo, Colors, Style
)


def get_all_children(flight_control: FlightControl) -> List[Dict[str, Any]]:
    """
    Get all child CIDs from Flight Control.

    Args:
        flight_control: FlightControl API instance

    Returns:
        List of child CID dictionaries
    """
    print_info("Retrieving Child CIDs from Flight Control...")

    query_response = flight_control.query_children()

    if not check_response(query_response, "Query children"):
        return []

    child_cids = extract_resources(query_response)

    if not child_cids:
        print_warning("No child CIDs found")
        return []

    # Get details for each child
    details_response = flight_control.get_children(ids=child_cids)

    if not check_response(details_response, "Get child details"):
        return []

    children = extract_resources(details_response)

    print_success(f"Found {len(children)} child CID(s)")
    return children


def get_all_custom_ioas(custom_ioa: CustomIOA, include_disabled: bool = False) -> List[Dict[str, Any]]:
    """
    Get all Custom IOA rule groups from Parent CID.

    Args:
        custom_ioa: CustomIOA API instance
        include_disabled: If False (default), only return enabled IOAs

    Returns:
        List of Custom IOA rule groups
    """
    print_info("Retrieving Custom IOAs from Parent CID...")

    # Query rule groups
    query_response = custom_ioa.query_rule_groups()

    if not check_response(query_response, "Query Custom IOA rule groups"):
        return []

    rule_group_ids = extract_resources(query_response)

    if not rule_group_ids:
        print_warning("No Custom IOAs found in Parent CID")
        return []

    # Get details for rule groups
    details_response = custom_ioa.get_rule_groups(ids=rule_group_ids)

    if not check_response(details_response, "Get Custom IOA details"):
        return []

    rule_groups = extract_resources(details_response)

    # Filter by enabled status unless include_disabled is True
    if not include_disabled:
        enabled_count = len(rule_groups)
        rule_groups = [rg for rg in rule_groups if rg.get('enabled', False)]
        disabled_count = enabled_count - len(rule_groups)

        if disabled_count > 0:
            print_info(f"Filtered out {disabled_count} disabled IOA(s)")

    print_success(f"Found {len(rule_groups)} Custom IOA rule group(s)" + (" (enabled only)" if not include_disabled else ""))
    return rule_groups


def select_custom_ioas(ioas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Interactive selection of Custom IOAs to replicate.

    Args:
        ioas: List of Custom IOA rule groups

    Returns:
        List of selected IOAs
    """
    print_header("SELECT CUSTOM IOAs TO REPLICATE", width=80)

    print()
    print(f"{Colors.INFO}Available Custom IOAs:{Colors.RESET}\n")

    for i, ioa in enumerate(ioas, 1):
        name = ioa.get('name', 'Unnamed')
        description = ioa.get('description', '')
        ioa_id = ioa.get('id', '')
        enabled = ioa.get('enabled', False)
        rule_count = len(ioa.get('rules', []))

        status = f"{Colors.SUCCESS}Enabled{Colors.RESET}" if enabled else f"{Colors.WARNING}Disabled{Colors.RESET}"

        print(f"  {Colors.HIGHLIGHT}[{i}]{Colors.RESET} {Colors.BRIGHT}{name}{Colors.RESET} ({status})")
        if description:
            print(f"      {Colors.DIM}Description: {description}{Colors.RESET}")
        print(f"      {Colors.DIM}ID: {ioa_id}{Colors.RESET}")
        print(f"      {Colors.DIM}Rules: {rule_count}{Colors.RESET}")
        print()

    print(f"{Colors.INFO}Selection options:{Colors.RESET}")
    print("  • Enter IOA numbers separated by commas (e.g., 1,3,5)")
    print("  • Enter 'all' to select all Custom IOAs")
    print("  • Enter 'q' to quit")
    print()

    while True:
        selection = input(f"{Colors.HIGHLIGHT}Select Custom IOAs to replicate: {Colors.RESET}").strip().lower()

        if selection == 'q':
            print_warning("Replication cancelled")
            sys.exit(0)

        if selection == 'all':
            print_success(f"Selected all {len(ioas)} Custom IOA(s)")
            return ioas

        try:
            numbers = [int(n.strip()) for n in selection.split(',')]
            if not all(1 <= n <= len(ioas) for n in numbers):
                print_error(f"Invalid selection. Enter numbers between 1 and {len(ioas)}")
                continue

            selected = [ioas[n-1] for n in numbers]
            print_success(f"Selected {len(selected)} Custom IOA(s):")
            for ioa in selected:
                print(f"  • {ioa['name']}")
            print()
            return selected

        except (ValueError, IndexError):
            print_error("Invalid input. Please enter numbers separated by commas, 'all', or 'q'")


def select_children(children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Interactive selection of Child CIDs.

    Args:
        children: List of child CIDs

    Returns:
        List of selected children
    """
    print_header("SELECT CHILD CIDs FOR REPLICATION", width=80)

    print()
    print(f"{Colors.INFO}Available Child CIDs:{Colors.RESET}\n")

    for i, child in enumerate(children, 1):
        name = child.get('name', 'Unknown')
        cid = child.get('child_cid', 'Unknown')

        print(f"  {Colors.HIGHLIGHT}[{i}]{Colors.RESET} {Colors.BRIGHT}{name}{Colors.RESET}")
        print(f"      {Colors.DIM}CID: {cid}{Colors.RESET}")
        print()

    print(f"{Colors.INFO}Selection options:{Colors.RESET}")
    print("  • Enter CID numbers separated by commas (e.g., 1,2,4)")
    print("  • Enter 'all' to select all Child CIDs")
    print("  • Enter 'q' to quit")
    print()

    while True:
        selection = input(f"{Colors.HIGHLIGHT}Select Child CIDs: {Colors.RESET}").strip().lower()

        if selection == 'q':
            print_warning("Replication cancelled")
            sys.exit(0)

        if selection == 'all':
            print_success(f"Selected all {len(children)} Child CID(s)")
            return children

        try:
            numbers = [int(n.strip()) for n in selection.split(',')]
            if not all(1 <= n <= len(children) for n in numbers):
                print_error(f"Invalid selection. Enter numbers between 1 and {len(children)}")
                continue

            selected = [children[n-1] for n in numbers]
            print_success(f"Selected {len(selected)} Child CID(s):")
            for child in selected:
                print(f"  • {child['name']}")
            print()
            return selected

        except (ValueError, IndexError):
            print_error("Invalid input. Please enter numbers separated by commas, 'all', or 'q'")


def ask_apply_to_policies() -> bool:
    """
    Ask user if they want to apply IOAs to prevention policies.

    Returns:
        True if user wants to apply, False otherwise
    """
    print()
    print_section("PREVENTION POLICIES", char="─", width=80)
    print()
    print(f"{Colors.WARNING}Do you want to apply the replicated Custom IOAs to ALL prevention policies in the Child CIDs?{Colors.RESET}")
    print()
    print("  • This will link each replicated IOA to all prevention policies matching the IOA platform")
    print("  • The IOAs will be enforced on hosts using those policies")
    print()

    while True:
        choice = input(f"{Colors.HIGHLIGHT}Apply to all prevention policies? (yes/no): {Colors.RESET}").strip().lower()

        if choice in ['yes', 'y']:
            print_success("Will apply IOAs to all prevention policies")
            return True
        elif choice in ['no', 'n']:
            print_info("IOAs will be replicated but not applied to policies")
            return False
        else:
            print_error("Please answer 'yes' or 'no'")


def replicate_ioa_to_child(ioa: Dict[str, Any], child_cid: str, client_id: str, client_secret: str, base_url: str) -> Optional[str]:
    """
    Replicate a Custom IOA to a Child CID.

    Checks if Rule Group already exists and only creates missing elements:
    - If Rule Group doesn't exist: Creates Rule Group + all Rules
    - If Rule Group exists: Only creates missing Rules
    - If everything exists: Skips with informative message

    Args:
        ioa: IOA rule group to replicate
        child_cid: Target Child CID
        client_id: API client ID
        client_secret: API client secret
        base_url: API base URL

    Returns:
        IOA rule group ID in child (new or existing), or None if failed
    """
    import time
    import threading

    # Spinner for replication
    spinner_running = True
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def spinner():
        idx = 0
        while spinner_running:
            sys.stdout.write(f'\r    {Colors.INFO}{spinner_chars[idx % len(spinner_chars)]}{Colors.RESET} Checking "{ioa["name"][:40]}"...')
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    spinner_thread = threading.Thread(target=spinner, daemon=True)
    spinner_thread.start()

    try:
        # Create API instance for Child CID
        child_ioa_api = CustomIOA(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            member_cid=child_cid
        )

        # Check if Rule Group already exists (search by name)
        query_response = child_ioa_api.query_rule_groups()
        existing_rule_group_id = None
        existing_rules = []
        existing_groups = []
        existing_rule_group_enabled = True

        if query_response.get('status_code') == 200:
            existing_ids = extract_resources(query_response)
            if existing_ids:
                # Get details to find matching name
                details_response = child_ioa_api.get_rule_groups(ids=existing_ids)
                if details_response.get('status_code') == 200:
                    existing_groups = extract_resources(details_response)
                    for group in existing_groups:
                        if group.get('name') == ioa.get('name'):
                            existing_rule_group_id = group['id']
                            existing_rules = group.get('rules', [])
                            existing_rule_group_enabled = group.get('enabled', True)
                            break

        # Determine what needs to be created
        rule_group_id = existing_rule_group_id
        rules_to_create = []
        source_rules = ioa.get('rules', [])

        if existing_rule_group_id:
            # Rule Group exists - check which rules are missing
            existing_rule_names = {rule.get('name') for rule in existing_rules}
            rules_to_create = [
                rule for rule in source_rules
                if rule.get('name') not in existing_rule_names
            ]
        else:
            # Rule Group doesn't exist - need to create everything
            rules_to_create = source_rules

        spinner_running = False
        time.sleep(0.2)
        sys.stdout.write('\r' + ' ' * 100 + '\r')
        sys.stdout.flush()

        # If Rule Group doesn't exist, create it
        if not existing_rule_group_id:
            payload = {
                "name": ioa.get('name'),
                "description": ioa.get('description', ''),
                "platform": ioa.get('platform'),
                "enabled": True  # Always create enabled IOAs
            }

            create_response = child_ioa_api.create_rule_group(**payload)

            if create_response['status_code'] in [200, 201]:
                rule_group_id = extract_resources(create_response)[0]['id']
                print_success(f"    ✓ Created Rule Group: {ioa['name']}")

                # Small delay to let the Rule Group be fully created
                time.sleep(1)
            else:
                print_error(f"    ✗ Failed to create Rule Group: {ioa['name']}")
                return None
        else:
            print_info(f"    ⟳ Rule Group already exists: {ioa['name']}")

            # Check if Rule Group is disabled and enable it
            if not existing_rule_group_enabled:
                try:
                    # Get current version
                    details_response = child_ioa_api.get_rule_groups(ids=[existing_rule_group_id])
                    if details_response.get('status_code') == 200:
                        current_details = extract_resources(details_response)[0]
                        update_response = child_ioa_api.update_rule_group(
                            id=existing_rule_group_id,
                            enabled=True,
                            name=ioa.get('name'),
                            description=ioa.get('description') if ioa.get('description') else "Auto-replicated IOA",
                            comment=ioa.get('comment') if ioa.get('comment') else "Enabled by replication script",
                            rulegroup_version=current_details.get('version')
                        )
                        if update_response.get('status_code') in [200, 201]:
                            print_success(f"      ✓ Enabled Rule Group")
                except Exception as e:
                    print_warning(f"      ⚠ Could not enable Rule Group: {str(e)}")

        # Create missing rules
        if rules_to_create:
            rules_created = 0
            rules_failed = 0

            for rule in rules_to_create:
                rule_payload = {
                    "rulegroup_id": rule_group_id,  # CRITICAL: Use rulegroup_id not rule_group_id!
                    "name": rule.get('name'),
                    "description": rule.get('description', ''),
                    "pattern_severity": rule.get('pattern_severity'),
                    "ruletype_id": rule.get('ruletype_id'),
                    "disposition_id": rule.get('disposition_id'),
                    "field_values": rule.get('field_values', [])
                }

                try:
                    rule_response = child_ioa_api.create_rule(**rule_payload)
                    if rule_response.get('status_code') in [200, 201]:
                        rules_created += 1
                    else:
                        rules_failed += 1
                        # Log the actual error
                        error_msg = "Unknown error"
                        if 'body' in rule_response and 'errors' in rule_response['body']:
                            errors = rule_response['body']['errors']
                            if errors:
                                error_msg = errors[0].get('message', 'Unknown error')
                        print_warning(f"      ⚠ Rule '{rule.get('name')}' failed: {error_msg}")
                except Exception as e:
                    rules_failed += 1
                    print_warning(f"      ⚠ Rule '{rule.get('name')}' exception: {str(e)}")

            # Report results
            if rules_created > 0:
                print_success(f"      ✓ Created {rules_created} rule(s)")
            if existing_rules:
                print_info(f"      ℹ {len(existing_rules)} rule(s) already existed")
        else:
            # Everything already exists
            if existing_rules:
                print_info(f"      ℹ All {len(existing_rules)} rule(s) already exist - skipping")
            else:
                print_warning(f"      ⚠ Rule Group exists but has no rules")

        # ALWAYS check and enable Rule Group and Rules (whether new or existing)
        try:
            # Re-query to get current state
            verify_response = child_ioa_api.get_rule_groups(ids=[rule_group_id])
            if verify_response.get('status_code') == 200:
                current_group = extract_resources(verify_response)[0]

                if not current_group.get('enabled'):
                    # Enable the Rule Group - need correct parameters
                    update_response = child_ioa_api.update_rule_group(
                        id=rule_group_id,
                        enabled=True,
                        name=ioa.get('name'),
                        description=ioa.get('description') if ioa.get('description') else "Auto-replicated IOA",
                        comment=ioa.get('comment') if ioa.get('comment') else "Enabled by replication script",
                        rulegroup_version=current_group.get('version')
                    )
                    if update_response.get('status_code') in [200, 201]:
                        print_success(f"      ✓ Enabled Rule Group")
                        # Re-fetch to get updated version
                        verify_response = child_ioa_api.get_rule_groups(ids=[rule_group_id])
                        if verify_response.get('status_code') == 200:
                            current_group = extract_resources(verify_response)[0]

                # Enable all Rules in the Rule Group
                rules_in_group = current_group.get('rules', [])
                disabled_rules = [r for r in rules_in_group if not r.get('enabled')]

                if disabled_rules:
                    enabled_count = 0
                    current_version = current_group.get('version')

                    for rule in disabled_rules:
                        # Build complete rule structure required by update_rules API
                        rule_update = {
                            "instance_id": rule.get('instance_id'),
                            "enabled": True,
                            "name": rule.get('name'),
                            "description": rule.get('description'),
                            "disposition_id": rule.get('disposition_id'),
                            "pattern_severity": rule.get('pattern_severity'),
                            "field_values": rule.get('field_values', []),
                            "rulegroup_version": current_version
                        }

                        try:
                            enable_response = child_ioa_api.update_rules(
                                rulegroup_id=rule_group_id,
                                rulegroup_version=current_version,
                                rule_updates=rule_update,
                                comment="Enabled by replication script"
                            )
                            if enable_response.get('status_code') in [200, 201]:
                                enabled_count += 1
                                # Re-fetch to get updated version for next rule
                                verify_response = child_ioa_api.get_rule_groups(ids=[rule_group_id])
                                if verify_response.get('status_code') == 200:
                                    current_group = extract_resources(verify_response)[0]
                                    current_version = current_group.get('version')
                        except Exception:
                            pass

                    if enabled_count > 0:
                        print_success(f"      ✓ Enabled {enabled_count} rule(s)")
        except Exception as e:
            print_warning(f"      ⚠ Could not enable elements: {str(e)}")

        return rule_group_id

    except Exception as e:
        spinner_running = False
        time.sleep(0.2)
        sys.stdout.write('\r' + ' ' * 100 + '\r')
        sys.stdout.flush()
        print_error(f"      ✗ Error: {str(e)}")
        return None


def apply_ioa_to_policies(ioa_id: str, ioa_platform: str, child_cid: str, client_id: str, client_secret: str, base_url: str) -> int:
    """
    Apply an IOA to all prevention policies in a Child CID that match the IOA platform.

    Args:
        ioa_id: IOA rule group ID
        ioa_platform: IOA platform (windows, mac, linux)
        child_cid: Child CID
        client_id: API client ID
        client_secret: API client secret
        base_url: API base URL

    Returns:
        Number of policies the IOA was applied to
    """
    import time
    import threading

    prevention = PreventionPolicy(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        member_cid=child_cid
    )

    # Get all prevention policies with details
    query_response = prevention.queryCombinedPreventionPolicies()

    if query_response['status_code'] != 200:
        return 0

    policies = extract_resources(query_response)

    if not policies:
        return 0

    # Filter policies by matching platform
    matching_policies = [
        p for p in policies
        if p.get('platform_name', '').lower() == ioa_platform.lower()
    ]

    if not matching_policies:
        return 0

    # Spinner for applying to policies
    spinner_running = True
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def spinner():
        idx = 0
        while spinner_running:
            sys.stdout.write(f'\r      {Colors.INFO}{spinner_chars[idx % len(spinner_chars)]}{Colors.RESET} Applying to {len(matching_policies)} {ioa_platform} prevention policies...')
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    spinner_thread = threading.Thread(target=spinner, daemon=True)
    spinner_thread.start()

    applied_count = 0

    try:
        for policy in matching_policies:
            policy_id = policy['id']

            # Check if IOA is already assigned
            current_ioa_groups = policy.get('ioa_rule_groups', [])
            ioa_ids = [g.get('id') if isinstance(g, dict) else g for g in current_ioa_groups]

            if ioa_id not in ioa_ids:
                # Use performPreventionPoliciesAction with add-rule-group
                action_params = [{
                    "name": "rule_group_id",
                    "value": ioa_id
                }]

                response = prevention.perform_policies_action(
                    action_name="add-rule-group",
                    action_parameters=action_params,
                    ids=[policy_id]
                )

                if response['status_code'] in [200, 201]:
                    applied_count += 1
            else:
                # Already assigned
                applied_count += 1

    finally:
        spinner_running = False
        time.sleep(0.2)
        sys.stdout.write('\r' + ' ' * 120 + '\r')
        sys.stdout.flush()

    return applied_count


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Replicate Custom IOAs from Parent to Child CIDs'
    )
    parser.add_argument(
        '--config',
        type=str,
        help='Path to credentials config file'
    )
    parser.add_argument(
        '--client-id',
        type=str,
        help='Falcon API Client ID'
    )
    parser.add_argument(
        '--client-secret',
        type=str,
        help='Falcon API Client Secret'
    )
    parser.add_argument(
        '--base-url',
        type=str,
        default='https://api.crowdstrike.com',
        help='Falcon API base URL'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Replicate all IOAs to all children without prompting'
    )

    args = parser.parse_args()

    print_jg_logo()
    print_header("FLIGHT CONTROL - CUSTOM IOAs REPLICATOR", width=80, color=Colors.SUCCESS)

    # Get credentials
    client_id, client_secret, base_url, source = get_credentials_smart(
        config_path=args.config,
        client_id=args.client_id,
        client_secret=args.client_secret,
        base_url=args.base_url
    )

    if not client_id or not client_secret:
        print_error("No credentials provided!")
        print()
        print("Please provide credentials via one of these methods:")
        print("  1. Config file: --config config/credentials.json")
        print("  2. CLI args: --client-id <id> --client-secret <secret>")
        print("  3. Environment variables: FALCON_CLIENT_ID, FALCON_CLIENT_SECRET")
        sys.exit(1)

    from utils.formatting import print_credentials_source
    print_credentials_source(source)

    # Authenticate
    print_info("Authenticating to Falcon API...")

    try:
        custom_ioa = CustomIOA(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
        flight_control = FlightControl(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
        print_success("Authentication successful!")
    except Exception as e:
        print_error(f"Authentication failed: {str(e)}")
        sys.exit(1)

    # Important notice about enabled IOAs only
    print()
    print_warning("IMPORTANT: Only ENABLED Custom IOA Rule Groups will be displayed and replicated.")
    print_info("Disabled IOAs are filtered out automatically to match Falcon console behavior.")
    print()

    # Get Custom IOAs from Parent
    print_section("RETRIEVING CUSTOM IOAs", width=80)
    ioas = get_all_custom_ioas(custom_ioa)

    if not ioas:
        print_error("No Custom IOAs found to replicate")
        sys.exit(1)

    # Get Child CIDs
    print()
    children = get_all_children(flight_control)

    if not children:
        print_error("No Child CIDs found")
        sys.exit(1)

    # Interactive or non-interactive mode
    if args.non_interactive:
        print_info("Non-interactive mode: replicating all IOAs to all children")
        selected_ioas = ioas
        selected_children = children
        apply_to_policies = False
    else:
        # Select IOAs
        print()
        selected_ioas = select_custom_ioas(ioas)

        # Select Children
        print()
        selected_children = select_children(children)

        # Ask about policies
        apply_to_policies = ask_apply_to_policies()

    # Warning about execution time
    if apply_to_policies:
        print()
        print_warning("NOTE: Applying IOAs to prevention policies can take several minutes per Child CID.")
        print_info("Please be patient during the policy application phase.")
        print()

    # Start replication
    print()
    print_header("REPLICATING CUSTOM IOAs", width=80)

    total_operations = len(selected_ioas) * len(selected_children)
    current_operation = 0
    success_count = 0
    failed_count = 0

    for child in selected_children:
        child_name = child['name']
        child_cid = child['child_cid']

        print()
        print(f"{Colors.HIGHLIGHT}▶ Target: {child_name}{Colors.RESET}")

        for ioa in selected_ioas:
            current_operation += 1

            # Replicate IOA
            new_ioa_id = replicate_ioa_to_child(ioa, child_cid, client_id, client_secret, base_url)

            if new_ioa_id:
                print_success(f"    ✓ Replicated: {ioa['name']}")
                success_count += 1

                # Apply to policies if requested
                if apply_to_policies and new_ioa_id:
                    policies_count = apply_ioa_to_policies(
                        new_ioa_id, ioa['platform'], child_cid, client_id, client_secret, base_url
                    )
                    if policies_count > 0:
                        print_info(f"      Applied to {policies_count} prevention policy/policies")
            else:
                print_error(f"    ✗ Failed: {ioa['name']}")
                failed_count += 1

            # Progress bar
            print_progress(
                current_operation,
                total_operations,
                prefix="Overall progress",
                suffix=f"({child_name[:30]})"
            )

    # Summary
    print()
    print_summary_box(
        "REPLICATION COMPLETE",
        {
            'Custom IOAs replicated': len(selected_ioas),
            'Child CIDs targeted': len(selected_children),
            'Total operations': total_operations,
            'Successful': success_count,
            'Failed': failed_count,
            'Applied to policies': 'Yes' if apply_to_policies else 'No'
        },
        width=80
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_warning("Replication interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

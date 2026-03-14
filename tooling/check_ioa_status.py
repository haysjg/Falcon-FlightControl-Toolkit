#!/usr/bin/env python3
"""Check the enabled status of replicated IOAs in Child CIDs."""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from falconpy import CustomIOA, FlightControl
from utils.auth import get_credentials_smart
from utils.common import extract_resources

def main():
    # Get credentials
    client_id, client_secret, base_url, source = get_credentials_smart(
        config_path="../config/credentials.json"
    )

    # Get children
    flight_control = FlightControl(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url
    )

    query_response = flight_control.query_children()
    child_cids = extract_resources(query_response)
    details_response = flight_control.get_children(ids=child_cids)
    children = extract_resources(details_response)

    print("\n" + "="*80)
    print("CHECKING IOA ENABLED STATUS IN CHILD CIDs")
    print("="*80)

    for child in children:
        child_name = child['name']
        child_cid = child['child_cid']

        print(f"\n▶ {child_name}")

        # Connect to child
        child_ioa = CustomIOA(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            member_cid=child_cid
        )

        # Query IOAs
        query_response = child_ioa.query_rule_groups()
        if query_response.get('status_code') != 200:
            print("  ✗ Failed to query")
            continue

        ioa_ids = extract_resources(query_response)
        if not ioa_ids:
            print("  ℹ No IOAs found")
            continue

        # Get details
        details_response = child_ioa.get_rule_groups(ids=ioa_ids)
        if details_response.get('status_code') != 200:
            print("  ✗ Failed to get details")
            continue

        ioas = extract_resources(details_response)

        for ioa in ioas:
            rg_enabled = "✓ Enabled" if ioa.get('enabled') else "✗ Disabled"
            print(f"  Rule Group: {ioa['name']} - {rg_enabled}")

            rules = ioa.get('rules', [])
            if rules:
                for rule in rules:
                    rule_enabled = "✓ Enabled" if rule.get('enabled') else "✗ Disabled"
                    print(f"    Rule: {rule['name']} - {rule_enabled}")
            else:
                print(f"    ℹ No rules")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

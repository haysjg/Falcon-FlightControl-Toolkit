#!/usr/bin/env python3
"""Detailed verification of IOA assignments to prevention policies."""

import sys
from pathlib import Path
import json

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from falconpy import PreventionPolicy, CustomIOA, FlightControl
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
    print("DETAILED IOA POLICY ASSIGNMENT VERIFICATION")
    print("="*80)

    for child in children:
        child_name = child['name']
        child_cid = child['child_cid']

        print(f"\n▶ {child_name}")
        print(f"  CID: {child_cid}")

        # Get IOAs in this child
        child_ioa = CustomIOA(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            member_cid=child_cid
        )

        ioa_query = child_ioa.query_rule_groups()
        if ioa_query.get('status_code') != 200:
            print("  ✗ Failed to query IOAs")
            continue

        ioa_ids = extract_resources(ioa_query)
        if not ioa_ids:
            print("  ℹ No IOAs found")
            continue

        ioa_details = child_ioa.get_rule_groups(ids=ioa_ids)
        ioas = extract_resources(ioa_details)

        print(f"\n  IOAs in this CID:")
        for ioa in ioas:
            print(f"    - {ioa['name']} ({ioa['platform']}) - ID: {ioa['id']}")

        # Get prevention policies
        prevention = PreventionPolicy(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            member_cid=child_cid
        )

        policy_query = prevention.queryCombinedPreventionPolicies()
        if policy_query.get('status_code') != 200:
            print("  ✗ Failed to query policies")
            continue

        policies = extract_resources(policy_query)

        print(f"\n  Prevention Policies ({len(policies)} total):")

        # Group by platform
        platforms = {}
        for policy in policies:
            platform = policy.get('platform_name', 'Unknown')
            if platform not in platforms:
                platforms[platform] = []
            platforms[platform].append(policy)

        for platform, platform_policies in platforms.items():
            print(f"\n  {platform} Policies ({len(platform_policies)}):")

            for policy in platform_policies[:5]:  # Show first 5 of each platform
                policy_name = policy.get('name', 'Unnamed')
                policy_id = policy.get('id')
                ioa_groups = policy.get('ioa_rule_groups', [])

                if ioa_groups:
                    print(f"    ✓ {policy_name}")
                    for ioa in ioa_groups:
                        if isinstance(ioa, dict):
                            print(f"        - {ioa.get('name', 'Unknown')} ({ioa.get('id', 'N/A')[:16]}...)")
                        else:
                            print(f"        - {ioa}")
                else:
                    print(f"    ✗ {policy_name} - No IOAs assigned")

            if len(platform_policies) > 5:
                print(f"    ... and {len(platform_policies) - 5} more")

        print()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

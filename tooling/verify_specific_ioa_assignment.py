#!/usr/bin/env python3
"""Verify specific IOA assignment to prevention policies."""

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

from falconpy import PreventionPolicy, CustomIOA, FlightControl
from utils.auth import get_credentials_smart
from utils.common import extract_resources

def main():
    # Get credentials
    client_id, client_secret, base_url, source = get_credentials_smart(
        config_path="../config/credentials.json"
    )

    # IOA name we're looking for
    target_ioa_name = "KeePass targeting activity"

    print("\n" + "="*80)
    print(f"VERIFYING ASSIGNMENT OF: {target_ioa_name}")
    print("="*80)

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

    for child in children:
        child_name = child['name']
        child_cid = child['child_cid']

        print(f"\n{'='*80}")
        print(f"Child CID: {child_name}")
        print(f"CID: {child_cid}")
        print("="*80)

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

        # Find our target IOA
        target_ioa = None
        for ioa in ioas:
            if ioa['name'] == target_ioa_name:
                target_ioa = ioa
                break

        if not target_ioa:
            print(f"  ℹ IOA '{target_ioa_name}' not found in this CID")
            continue

        print(f"\n  ✓ Found IOA: {target_ioa['name']}")
        print(f"    ID: {target_ioa['id']}")
        print(f"    Platform: {target_ioa['platform']}")

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

        # Filter Windows policies only (since our IOA is Windows)
        windows_policies = [
            p for p in policies
            if p.get('platform_name', '').lower() == target_ioa['platform'].lower()
        ]

        print(f"\n  Total {target_ioa['platform']} policies: {len(windows_policies)}")

        # Find policies with our IOA assigned
        assigned_policies = []
        for policy in windows_policies:
            ioa_groups = policy.get('ioa_rule_groups', [])
            for ioa in ioa_groups:
                if isinstance(ioa, dict) and ioa.get('id') == target_ioa['id']:
                    assigned_policies.append(policy)
                    break

        if assigned_policies:
            print(f"\n  ✓ IOA IS ASSIGNED TO {len(assigned_policies)} POLICIES:")
            print("\n  Policy Details (copy these IDs to check in console):")
            for policy in assigned_policies:
                print(f"\n    Policy Name: {policy['name']}")
                print(f"    Policy ID:   {policy['id']}")
                print(f"    Description: {policy.get('description', 'N/A')}")
                print(f"    Enabled:     {policy.get('enabled', False)}")

                # Show all IOAs on this policy
                ioa_groups = policy.get('ioa_rule_groups', [])
                if len(ioa_groups) > 1:
                    print(f"    Other IOAs:  {len(ioa_groups) - 1} additional IOA(s)")
        else:
            print(f"\n  ✗ IOA IS NOT ASSIGNED TO ANY {target_ioa['platform']} POLICIES")
            print(f"    (Checked {len(windows_policies)} {target_ioa['platform']} policies)")

    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
    print("\nTo check in console:")
    print("1. Go to Configuration > Prevention Policies")
    print("2. Select the Child CID from the dropdown")
    print("3. Search for one of the policy names listed above")
    print("4. Click on the policy")
    print("5. Look in the 'Custom Indicators of Attack (IOAs)' section")
    print("="*80 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

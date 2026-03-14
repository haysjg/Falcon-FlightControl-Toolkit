#!/usr/bin/env python3
"""
Check Precedence Structure in Firewall Management API

This diagnostic script examines how precedence is structured in:
1. Rules within Rule Groups
2. Rule Groups within Policies
"""

import sys
import os

# Fix Windows console encoding issues
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from falconpy import OAuth2, FirewallManagement, FirewallPolicies
from utils.auth import get_credentials_smart
from utils.formatting import print_header, print_section, print_info, print_success, print_error
import json

def main():
    print_header("FIREWALL PRECEDENCE STRUCTURE CHECK")

    # Authenticate - try config file first, then env vars
    try:
        from utils.auth import load_credentials_from_file
        creds = load_credentials_from_file('../config/credentials.json')
        client_id = creds['client_id']
        client_secret = creds['client_secret']
        base_url = creds.get('base_url', 'https://api.crowdstrike.com')
        print_success("✓ Using credentials from config file")
    except:
        # Try environment variables
        from utils.auth import load_credentials_from_env
        env_creds = load_credentials_from_env()
        if not env_creds:
            print_error("No credentials found in config file or environment variables")
            return 1
        client_id = env_creds['client_id']
        client_secret = env_creds['client_secret']
        base_url = env_creds.get('base_url', 'https://api.crowdstrike.com')
        print_success("✓ Using credentials from environment variables")

    auth = OAuth2(client_id=client_id, client_secret=client_secret, base_url=base_url)
    token_result = auth.token()

    if token_result.get('status_code') != 201:
        print_error(f"Authentication failed: {token_result}")
        return 1

    print_success("✓ Authenticated")

    falcon_fw = FirewallManagement(auth_object=auth)
    falcon_fp = FirewallPolicies(auth_object=auth)

    # 1. Check Rule Groups with Rules
    print_section("RULE GROUPS AND RULES")

    query_response = falcon_fw.query_rule_groups()

    if query_response['status_code'] != 200:
        print_error(f"Failed to query rule groups: {query_response['body'].get('errors')}")
        return 1

    rg_ids = query_response['body'].get('resources', [])
    print_info(f"Found {len(rg_ids)} total Rule Groups")

    # Get details for first few rule groups
    if rg_ids:
        details_response = falcon_fw.get_rule_groups(ids=rg_ids[:5])

        if details_response['status_code'] == 200:
            for rg in details_response['body'].get('resources', []):
                print_info(f"\nRule Group: {rg.get('name')}")
                print_info(f"  ID: {rg.get('id')}")
                print_info(f"  Platform: {rg.get('platform')}")

                rules = rg.get('rules', [])
                print_info(f"  Rules count: {len(rules)}")

                if rules:
                    print_info(f"\n  First rule structure:")
                    first_rule = rules[0]
                    print_info(f"    Keys: {list(first_rule.keys())}")

                    # Check for precedence field
                    if 'precedence' in first_rule:
                        print_success(f"    ✓ Precedence field found: {first_rule['precedence']}")
                    else:
                        print_error(f"    ✗ No precedence field")

                    # Show all rules with precedence if available
                    if len(rules) > 1:
                        print_info(f"\n  All rules in this group:")
                        for rule in rules:
                            prec = rule.get('precedence', 'N/A')
                            name = rule.get('name', 'Unknown')
                            print_info(f"    - {name} (precedence: {prec})")

                # Show sample rule JSON
                if rules:
                    print_info(f"\n  Sample rule JSON:")
                    print(json.dumps(rules[0], indent=4))

                break  # Just check first group with rules

    # 2. Check Policy Containers with Rule Group assignments
    print_section("POLICIES AND RULE GROUP ASSIGNMENTS")

    query_policies = falcon_fp.query_policies()

    if query_policies['status_code'] != 200:
        print_error(f"Failed to query policies: {query_policies['body'].get('errors')}")
        return 1

    policy_ids = query_policies['body'].get('resources', [])
    print_info(f"Found {len(policy_ids)} total Policies")

    # Get details for first few policies
    if policy_ids:
        details_response = falcon_fp.get_policies(ids=policy_ids[:5])

        if details_response['status_code'] == 200:
            for policy in details_response['body'].get('resources', []):
                print_info(f"\nPolicy: {policy.get('name')}")
                print_info(f"  ID: {policy.get('id')}")

                # Check for rule_group_ids
                rg_ids_in_policy = policy.get('rule_group_ids', [])
                print_info(f"  Rule Groups assigned: {len(rg_ids_in_policy)}")

                if rg_ids_in_policy:
                    print_info(f"  Rule Group IDs (in order):")
                    for idx, rg_id in enumerate(rg_ids_in_policy):
                        print_info(f"    {idx + 1}. {rg_id}")

                    # Show policy JSON sample
                    print_info(f"\n  Sample policy JSON:")
                    print(json.dumps({
                        'name': policy.get('name'),
                        'id': policy.get('id'),
                        'rule_group_ids': policy.get('rule_group_ids', []),
                        'enabled': policy.get('enabled')
                    }, indent=4))

                break  # Just check first policy with RGs

    print_section("SUMMARY")
    print_info("Check the output above to confirm:")
    print_info("1. Rules have a 'precedence' field (numeric)")
    print_info("2. Policies have 'rule_group_ids' as an ordered array")

    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Check current firewall test data status
"""
import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from falconpy import OAuth2, FirewallManagement, FirewallPolicies
from utils.auth import get_credentials_smart
from utils.formatting import print_info, print_success, print_error, print_section, print_jg_logo

# Get credentials - try config file first, then environment variables
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'credentials.json')
if not os.path.exists(config_path):
    config_path = None  # Will fall back to env vars

client_id, client_secret, base_url, source = get_credentials_smart(config_path=config_path)

if not client_id or not client_secret:
    print_error("No credentials found. Set FALCON_CLIENT_ID and FALCON_CLIENT_SECRET environment variables or use config file.")
    sys.exit(1)

print_jg_logo()
print_section("CURRENT FIREWALL TEST DATA STATUS")
print_info(f"Using credentials from: {source}")
print()

# Create auth
auth = OAuth2(client_id=client_id, client_secret=client_secret, base_url=base_url)

# Generate token
token_result = auth.token()
if token_result['status_code'] != 201:
    print_error("Authentication failed")
    sys.exit(1)

falcon_fw = FirewallManagement(auth_object=auth)
falcon_fp = FirewallPolicies(auth_object=auth)

print_success("✓ Authentication successful")
print()

# Check Network Locations
print_info("Network Locations:")
response = falcon_fw.query_network_locations()
if response['status_code'] == 200:
    location_ids = response['body']['resources']
    print_success(f"  Total: {len(location_ids)}")

    # Get details for test data locations
    if location_ids:
        details = falcon_fw.get_network_locations(ids=location_ids)
        test_locations = [loc for loc in details['body'].get('resources', [])
                         if loc.get('name', '').lower().startswith('test')]
        print_info(f"  Test locations (Test*): {len(test_locations)}")
        for loc in test_locations[:5]:
            print_info(f"    • {loc.get('name')}")
        if len(test_locations) > 5:
            print_info(f"    ... and {len(test_locations) - 5} more")
else:
    print_error(f"  Failed to query: {response['body'].get('errors')}")
print()

# Check Rule Groups
print_info("Rule Groups:")
response = falcon_fw.query_rule_groups()
if response['status_code'] == 200:
    rg_ids = response['body']['resources']
    print_success(f"  Total: {len(rg_ids)}")

    # Get details for test data rule groups
    if rg_ids:
        details = falcon_fw.get_rule_groups(ids=rg_ids)
        test_rgs = [rg for rg in details['body'].get('resources', [])
                   if rg.get('name', '').lower().startswith('test')]
        print_info(f"  Test rule groups (Test*): {len(test_rgs)}")
        for rg in test_rgs[:5]:
            print_info(f"    • {rg.get('name')} ({rg.get('platform')})")
        if len(test_rgs) > 5:
            print_info(f"    ... and {len(test_rgs) - 5} more")
else:
    print_error(f"  Failed to query: {response['body'].get('errors')}")
print()

# Check Rules
print_info("Rules:")
response = falcon_fw.query_rules()
if response['status_code'] == 200:
    rule_ids = response['body']['resources']
    print_success(f"  Total: {len(rule_ids)}")

    # Get details for test data rules
    if rule_ids:
        details = falcon_fw.get_rules(ids=rule_ids[:100])  # Sample first 100
        test_rules = [r for r in details['body'].get('resources', [])
                     if r.get('name', '').lower().startswith('test')]
        print_info(f"  Test rules (Test*): {len(test_rules)} (sampled from first 100)")
        for rule in test_rules[:5]:
            print_info(f"    • {rule.get('name')} ({rule.get('action')})")
        if len(test_rules) > 5:
            print_info(f"    ... and {len(test_rules) - 5} more")
else:
    print_error(f"  Failed to query: {response['body'].get('errors')}")
print()

# Check Policies
print_info("Policies:")
response = falcon_fp.query_policies()
if response['status_code'] == 200:
    policy_ids = response['body']['resources']
    print_success(f"  Total: {len(policy_ids)}")

    # Get details for test data policies
    if policy_ids:
        details = falcon_fp.get_policies(ids=policy_ids)
        test_policies = [p for p in details['body'].get('resources', [])
                        if p.get('name', '').lower().startswith('test')]
        print_info(f"  Test policies (Test*): {len(test_policies)}")
        for policy in test_policies[:5]:
            print_info(f"    • {policy.get('name')} ({policy.get('platform_name')})")
        if len(test_policies) > 5:
            print_info(f"    ... and {len(test_policies) - 5} more")
else:
    print_error(f"  Failed to query: {response['body'].get('errors')}")
print()

print_section("RECOMMENDATION")
if test_locations or test_rgs or test_policies:
    print_info("Existing test data found. You can:")
    print_info("  1. Use existing test data for replication tests")
    print_info("  2. Run cleanup and regenerate fresh test data:")
    print_info("     python generate_firewall_test_data.py --cleanup-only --yes")
    print_info("     python generate_firewall_test_data.py --yes")
else:
    print_info("No test data found. Generate new test data:")
    print_info("  python generate_firewall_test_data.py --yes")

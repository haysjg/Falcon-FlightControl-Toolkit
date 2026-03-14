#!/usr/bin/env python3
"""
Fix test policies by assigning Rule Groups to them
"""
import sys
import os
import random

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
from utils.formatting import print_info, print_success, print_error, print_section, print_warning

print_section("FIX POLICY RULE GROUP ASSIGNMENTS")
print()

# Get credentials
client_id, client_secret, base_url, _ = get_credentials_smart(
    config_path='../../config/credentials.json'
)

# Initialize auth
auth = OAuth2(client_id=client_id, client_secret=client_secret, base_url=base_url)
auth.token()

falcon_fw = FirewallManagement(auth_object=auth)
falcon_fp = FirewallPolicies(auth_object=auth)

print_success("Authentication successful")
print()

# Step 1: Get all test Rule Groups by platform
print_info("Step 1: Retrieving Rule Groups...")
response = falcon_fw.query_rule_groups()
rg_ids = response['body']['resources']
details = falcon_fw.get_rule_groups(ids=rg_ids)

rgs_by_platform = {'windows': [], 'mac': [], 'linux': []}
for rg in details['body'].get('resources', []):
    if 'Test-' in rg.get('name', ''):
        platform = rg.get('platform', '').lower()
        if platform in rgs_by_platform:
            rgs_by_platform[platform].append(rg.get('id'))

print_success(f"Found test Rule Groups:")
for platform, rg_list in rgs_by_platform.items():
    print_info(f"  • {platform.capitalize()}: {len(rg_list)} rule groups")
print()

# Step 2: Get all test Policies
print_info("Step 2: Retrieving Policies...")
response = falcon_fp.query_policies()
policy_ids = response['body']['resources']
details = falcon_fp.get_policies(ids=policy_ids)

test_policies = [p for p in details['body'].get('resources', []) if 'Test-Policy' in p.get('name', '')]
print_success(f"Found {len(test_policies)} test policies")
print()

# Step 3: Assign Rule Groups to Policies
print_section("ASSIGNING RULE GROUPS TO POLICIES")
print()

success_count = 0
failed_count = 0

for policy in test_policies:
    policy_id = policy.get('id')
    policy_name = policy.get('name')
    platform_name = policy.get('platform_name', '').lower()

    # Map platform_name to platform key
    platform_key = platform_name
    if 'windows' in platform_name:
        platform_key = 'windows'
    elif 'mac' in platform_name:
        platform_key = 'mac'
    elif 'linux' in platform_name:
        platform_key = 'linux'

    # Select 2-3 random Rule Groups for this platform
    available_rgs = rgs_by_platform.get(platform_key, [])

    if not available_rgs:
        print_warning(f"No Rule Groups available for {policy_name} ({platform_name})")
        continue

    num_to_assign = min(3, len(available_rgs))
    selected_rgs = random.sample(available_rgs, num_to_assign)

    # Prepare update body
    update_body = {
        "policy_id": policy_id,
        "rule_group_ids": selected_rgs,
        "default_inbound": "ALLOW",
        "default_outbound": "ALLOW",
        "enforce": False,
        "local_logging": False,
        "tracking": "none",
        "test_mode": False
    }

    # Update policy container
    print_info(f"Assigning {len(selected_rgs)} Rule Groups to {policy_name}...")
    response = falcon_fw.update_policy_container(
        ids=policy_id,
        body=update_body
    )

    if response['status_code'] in [200, 201]:
        print_success(f"  Success - {len(selected_rgs)} Rule Groups assigned")
        success_count += 1
    else:
        print_error(f"  Failed: {response['body'].get('errors')}")
        print_error(f"  Status code: {response['status_code']}")
        print_error(f"  Body sent: {update_body}")
        failed_count += 1

print()
print_section("ASSIGNMENT COMPLETE")
print_success(f"Successfully updated: {success_count} policies")
if failed_count > 0:
    print_error(f"Failed to update: {failed_count} policies")
print()

# Step 4: Verify assignments
print_info("Verifying assignments...")
response = falcon_fp.query_policies()
policy_ids = response['body']['resources']
details = falcon_fp.get_policies(ids=policy_ids)

test_policies = [p for p in details['body'].get('resources', []) if 'Test-Policy' in p.get('name', '')]

policies_with_rgs = 0
for policy in test_policies:
    policy_id = policy.get('id')
    container = falcon_fw.get_policy_containers(ids=[policy_id])

    if container['status_code'] == 200 and container['body'].get('resources'):
        cont_data = container['body']['resources'][0]
        rg_ids = cont_data.get('rule_group_ids', [])
        if len(rg_ids) > 0:
            policies_with_rgs += 1

print_success(f"{policies_with_rgs}/{len(test_policies)} test policies now have Rule Groups assigned")
print()

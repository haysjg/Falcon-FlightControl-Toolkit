#!/usr/bin/env python3
"""
Clean up empty rule groups - keep only 2-3 for testing
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

from falconpy import OAuth2, FirewallManagement
from utils.auth import get_credentials_smart
from utils.formatting import print_info, print_success, print_error, print_warning, print_section

# Get credentials
client_id, client_secret, base_url, source = get_credentials_smart(
    config_path='../../config/credentials.json'
)

print_section("RULE GROUP CLEANUP - Remove Empty Groups")
print()

# Create auth
auth = OAuth2(client_id=client_id, client_secret=client_secret, base_url=base_url)
falcon_fw = FirewallManagement(auth_object=auth)

if not auth.token_status:
    print_error("Authentication failed")
    sys.exit(1)

print_success("✓ Authentication successful")
print()

# Query all rule groups
print_info("Querying all rule groups...")
response = falcon_fw.query_rule_groups()

if response['status_code'] != 200:
    print_error(f"Failed to query rule groups: {response['body'].get('errors')}")
    sys.exit(1)

rg_ids = response['body']['resources']
print_success(f"✓ Found {len(rg_ids)} rule groups")
print()

# Get details for all rule groups
print_info("Analyzing rule groups...")
response = falcon_fw.get_rule_groups(ids=rg_ids)

if response['status_code'] != 200:
    print_error(f"Failed to get rule group details: {response['body'].get('errors')}")
    sys.exit(1)

# Separate empty from non-empty
empty_groups = []
non_empty_groups = []

for rg in response['body'].get('resources', []):
    rg_id = rg.get('id')
    rg_name = rg.get('name', 'Unnamed')
    rules = rg.get('rules', [])

    if len(rules) == 0:
        empty_groups.append({'id': rg_id, 'name': rg_name})
    else:
        non_empty_groups.append({'id': rg_id, 'name': rg_name, 'rule_count': len(rules)})

print_success(f"✓ Analysis complete:")
print_info(f"  • Rule groups with rules: {len(non_empty_groups)}")
print_info(f"  • Empty rule groups: {len(empty_groups)}")
print()

if not empty_groups:
    print_success("No empty rule groups to clean up!")
    sys.exit(0)

# Keep first 3 empty groups for testing
keep_count = min(3, len(empty_groups))
to_keep = empty_groups[:keep_count]
to_delete = empty_groups[keep_count:]

print_section("CLEANUP PLAN")
print_info(f"Empty rule groups to KEEP (for testing): {keep_count}")
for rg in to_keep:
    print_info(f"  • {rg['name']} ({rg['id'][:12]}...)")
print()

print_warning(f"Empty rule groups to DELETE: {len(to_delete)}")
for rg in to_delete[:5]:  # Show first 5
    print_warning(f"  • {rg['name']} ({rg['id'][:12]}...)")
if len(to_delete) > 5:
    print_warning(f"  ... and {len(to_delete) - 5} more")
print()

if not to_delete:
    print_success("Only 3 or fewer empty rule groups exist - nothing to delete!")
    sys.exit(0)

# Confirmation
print_warning(f"⚠️  This will permanently delete {len(to_delete)} empty rule groups!")
confirm = input("Type 'yes' to proceed: ").strip().lower()

if confirm != 'yes':
    print_warning("Cleanup cancelled by user")
    sys.exit(0)

print()
print_section("DELETING EMPTY RULE GROUPS")

# Delete in batches (API might have limits)
batch_size = 20
deleted_count = 0

for i in range(0, len(to_delete), batch_size):
    batch = to_delete[i:i+batch_size]
    batch_ids = [rg['id'] for rg in batch]

    print_info(f"Deleting batch {i//batch_size + 1} ({len(batch)} groups)...")

    response = falcon_fw.delete_rule_groups(ids=batch_ids)

    if response['status_code'] in [200, 204]:
        deleted_count += len(batch)
        print_success(f"✓ Deleted {len(batch)} rule groups")
    else:
        print_error(f"Failed to delete batch: {response['body'].get('errors')}")

print()
print_section("CLEANUP COMPLETE")
print_success(f"✓ Deleted {deleted_count} empty rule groups")
print_info(f"✓ Kept {keep_count} empty rule groups for testing")
print()

# Show final stats
print_info("Final statistics:")
print_info(f"  • Total rule groups remaining: {len(non_empty_groups) + keep_count}")
print_info(f"  • Rule groups with rules: {len(non_empty_groups)}")
print_info(f"  • Empty rule groups (for testing): {keep_count}")

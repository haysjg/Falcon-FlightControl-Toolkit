#!/usr/bin/env python3
"""
Cleanup Test Data - Firewall Management (Child CIDs Only)

This script deletes test data from Child CIDs to prepare for replication testing.
It will delete FROM CHILD CIDS ONLY:
- Network Locations matching test patterns
- Rule Groups matching test patterns
- Policies matching test patterns

Test patterns: Test*, TestLoc*, TestRG*, TestPolicy*, Test-*

IMPORTANT: This script will DELETE resources from Child CIDs. Parent CID is NOT touched.
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

import argparse
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from falconpy import OAuth2, FirewallManagement, FirewallPolicies, FlightControl
from utils.auth import get_credentials_smart
from utils.formatting import (
    print_header, print_section, print_info, print_success,
    print_error, print_warning, print_jg_logo
)


class TestDataCleanup:
    """Handles cleanup of test Firewall Management data from Child CIDs"""

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.crowdstrike.com"):
        """Initialize the cleanup tool

        Args:
            client_id: CrowdStrike API Client ID
            client_secret: CrowdStrike API Client Secret
            base_url: API base URL (default: US-1)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url

        # Initialize API clients
        print_info("Authenticating to Falcon API...")

        # Create shared OAuth2 object
        self.auth = OAuth2(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )

        # Force token generation
        token_result = self.auth.token()
        if token_result.get('status_code') != 201:
            raise Exception(f"Authentication failed: {token_result.get('body')}")

        # Initialize service classes
        self.falcon_fw = FirewallManagement(auth_object=self.auth)
        self.falcon_fp = FirewallPolicies(auth_object=self.auth)
        self.falcon_fc = FlightControl(auth_object=self.auth)
        print_success("Authentication successful!")

        # Cache for CID data
        self.parent_cid = None
        self.child_cids = []
        self.cid_names = {}

    def get_child_cids(self) -> List[Dict[str, str]]:
        """Retrieve Child CIDs from Flight Control

        Returns:
            List of child CID dicts with 'name' and 'cid'
        """
        print_info("Retrieving Child CIDs from Flight Control...")

        # Query children
        response = self.falcon_fc.query_children()

        if response['status_code'] != 200:
            raise Exception(f"Failed to query CIDs: {response['body'].get('errors', 'Unknown error')}")

        child_cid_ids = response['body']['resources']

        if not child_cid_ids:
            print_warning("No Child CIDs found.")
            return []

        # Get child details
        details_response = self.falcon_fc.get_children(ids=child_cid_ids)

        if details_response['status_code'] != 200:
            raise Exception(f"Failed to get CID details: {details_response['body'].get('errors', 'Unknown error')}")

        children = []

        for cid_data in details_response['body']['resources']:
            cid_id = cid_data.get('id') or cid_data.get('child_cid')
            cid_name = cid_data.get('name', 'Unnamed CID')
            children.append({'name': cid_name, 'cid': cid_id})
            self.cid_names[cid_id] = cid_name

        self.child_cids = children
        print_success(f"  Found {len(children)} Child CID(s)")
        return children

    def is_test_resource(self, name: str) -> bool:
        """Check if a resource name matches test patterns

        Args:
            name: Resource name

        Returns:
            True if it's a test resource, False otherwise
        """
        test_patterns = [
            'Test-',
            'TestLoc',
            'TestRG',
            'TestPolicy',
            'Test_',
            'test-',
            'test_'
        ]

        for pattern in test_patterns:
            if name.startswith(pattern):
                return True

        return False

    def find_test_network_locations(self, cid: str) -> List[Dict[str, Any]]:
        """Find all test Network Locations in a specific CID

        Args:
            cid: CID to scan

        Returns:
            List of test Network Location dictionaries
        """
        cid_name = self.cid_names.get(cid, cid[:12])
        print_info(f"  Scanning {cid_name} for test Network Locations...")

        # Create auth for this CID
        cid_auth = OAuth2(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
            member_cid=cid
        )
        cid_auth.token()
        cid_fw = FirewallManagement(auth_object=cid_auth)

        # Query all locations
        query_response = cid_fw.query_network_locations()

        if query_response['status_code'] != 200:
            print_error(f"    Failed to query: {query_response['body'].get('errors')}")
            return []

        loc_ids = query_response['body'].get('resources', [])

        if not loc_ids:
            print_info("    No Network Locations found")
            return []

        # Get details
        details_response = cid_fw.get_network_locations(ids=loc_ids)

        if details_response['status_code'] != 200:
            print_error(f"    Failed to get details: {details_response['body'].get('errors')}")
            return []

        # Filter test locations
        test_locations = []
        for loc in details_response['body'].get('resources', []):
            if self.is_test_resource(loc.get('name', '')):
                loc['_cid'] = cid  # Tag with CID for deletion
                test_locations.append(loc)

        print_success(f"    Found {len(test_locations)} test location(s)")
        return test_locations

    def find_test_rule_groups(self, cid: str) -> List[Dict[str, Any]]:
        """Find all test Rule Groups in a specific CID

        Args:
            cid: CID to scan

        Returns:
            List of test Rule Group dictionaries
        """
        cid_name = self.cid_names.get(cid, cid[:12])
        print_info(f"  Scanning {cid_name} for test Rule Groups...")

        # Create auth for this CID
        cid_auth = OAuth2(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
            member_cid=cid
        )
        cid_auth.token()
        cid_fw = FirewallManagement(auth_object=cid_auth)

        # Query all rule groups
        query_response = cid_fw.query_rule_groups()

        if query_response['status_code'] != 200:
            print_error(f"    Failed to query: {query_response['body'].get('errors')}")
            return []

        rg_ids = query_response['body'].get('resources', [])

        if not rg_ids:
            print_info("    No Rule Groups found")
            return []

        # Get details
        details_response = cid_fw.get_rule_groups(ids=rg_ids)

        if details_response['status_code'] != 200:
            print_error(f"    Failed to get details: {details_response['body'].get('errors')}")
            return []

        # Filter test rule groups
        test_rule_groups = []
        for rg in details_response['body'].get('resources', []):
            if self.is_test_resource(rg.get('name', '')):
                rg['_cid'] = cid  # Tag with CID for deletion
                test_rule_groups.append(rg)

        print_success(f"    Found {len(test_rule_groups)} test rule group(s)")
        return test_rule_groups

    def find_test_policies(self, cid: str) -> List[Dict[str, Any]]:
        """Find all test Policies in a specific CID

        Args:
            cid: CID to scan

        Returns:
            List of test Policy dictionaries
        """
        cid_name = self.cid_names.get(cid, cid[:12])
        print_info(f"  Scanning {cid_name} for test Policies...")

        # Create auth for this CID
        cid_auth = OAuth2(
            client_id=self.client_id,
            client_secret=self.client_secret,
            base_url=self.base_url,
            member_cid=cid
        )
        cid_auth.token()
        cid_fp = FirewallPolicies(auth_object=cid_auth)

        # Query all policies
        query_response = cid_fp.query_policies()

        if query_response['status_code'] != 200:
            print_error(f"    Failed to query: {query_response['body'].get('errors')}")
            return []

        policy_ids = query_response['body'].get('resources', [])

        if not policy_ids:
            print_info("    No Policies found")
            return []

        # Get details
        details_response = cid_fp.get_policies(ids=policy_ids)

        if details_response['status_code'] != 200:
            print_error(f"    Failed to get details: {details_response['body'].get('errors')}")
            return []

        # Filter test policies
        test_policies = []
        for policy in details_response['body'].get('resources', []):
            if self.is_test_resource(policy.get('name', '')):
                policy['_cid'] = cid  # Tag with CID for deletion
                test_policies.append(policy)

        print_success(f"    Found {len(test_policies)} test polic(ies)")
        return test_policies

    def delete_policies(self, policies: List[Dict[str, Any]]) -> int:
        """Delete policies from their respective CIDs (optimized batch deletion)

        Args:
            policies: List of policy dictionaries to delete (with _cid tag)

        Returns:
            Number of successfully deleted policies
        """
        if not policies:
            return 0

        print_info(f"Deleting {len(policies)} Policies...")
        success_count = 0
        total = len(policies)

        # Group policies by CID for efficient batch deletion
        policies_by_cid = {}
        for policy in policies:
            cid = policy.get('_cid')
            if cid not in policies_by_cid:
                policies_by_cid[cid] = []
            policies_by_cid[cid].append(policy)

        # Process each CID
        processed = 0
        for cid, cid_policies in policies_by_cid.items():
            cid_name = self.cid_names.get(cid, cid[:12])

            # Create auth once per CID
            cid_auth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url,
                member_cid=cid
            )
            cid_auth.token()
            cid_fp = FirewallPolicies(auth_object=cid_auth)

            # Delete in batches of 100 (API limit)
            batch_size = 100
            for i in range(0, len(cid_policies), batch_size):
                batch = cid_policies[i:i + batch_size]
                batch_ids = [p.get('id') for p in batch]

                # Show progress
                progress_pct = (processed / total) * 100
                print(f"\r  Progress: {processed}/{total} ({progress_pct:.0f}%) - {cid_name[:30]:<30}", end='', flush=True)

                response = cid_fp.delete_policies(ids=batch_ids)

                if response['status_code'] in [200, 201]:
                    success_count += len(batch_ids)
                    processed += len(batch_ids)
                else:
                    # If batch fails, try individual deletions
                    for policy in batch:
                        single_response = cid_fp.delete_policies(ids=policy.get('id'))
                        if single_response['status_code'] in [200, 201]:
                            success_count += 1
                        processed += 1

        print()  # New line after progress
        print_success(f"✓ Deleted {success_count} Policies")
        return success_count

    def delete_rule_groups(self, rule_groups: List[Dict[str, Any]]) -> int:
        """Delete rule groups from their respective CIDs (optimized batch deletion)

        Args:
            rule_groups: List of rule group dictionaries to delete (with _cid tag)

        Returns:
            Number of successfully deleted rule groups
        """
        if not rule_groups:
            return 0

        print_info(f"Deleting {len(rule_groups)} Rule Groups...")
        success_count = 0
        total = len(rule_groups)

        # Group rule groups by CID for efficient batch deletion
        rgs_by_cid = {}
        for rg in rule_groups:
            cid = rg.get('_cid')
            if cid not in rgs_by_cid:
                rgs_by_cid[cid] = []
            rgs_by_cid[cid].append(rg)

        # Process each CID
        processed = 0
        for cid, cid_rgs in rgs_by_cid.items():
            cid_name = self.cid_names.get(cid, cid[:12])

            # Create auth once per CID
            cid_auth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url,
                member_cid=cid
            )
            cid_auth.token()
            cid_fw = FirewallManagement(auth_object=cid_auth)

            # Delete in batches of 100 (API limit)
            batch_size = 100
            for i in range(0, len(cid_rgs), batch_size):
                batch = cid_rgs[i:i + batch_size]
                batch_ids = [rg.get('id') for rg in batch]

                # Show progress
                progress_pct = (processed / total) * 100
                print(f"\r  Progress: {processed}/{total} ({progress_pct:.0f}%) - {cid_name[:30]:<30}", end='', flush=True)

                response = cid_fw.delete_rule_groups(ids=batch_ids)

                if response['status_code'] in [200, 201]:
                    success_count += len(batch_ids)
                    processed += len(batch_ids)
                else:
                    # If batch fails, try individual deletions
                    for rg in batch:
                        single_response = cid_fw.delete_rule_groups(ids=rg.get('id'))
                        if single_response['status_code'] in [200, 201]:
                            success_count += 1
                        processed += 1

        print()  # New line after progress
        print_success(f"✓ Deleted {success_count} Rule Groups")
        return success_count

        return success_count

    def delete_network_locations(self, locations: List[Dict[str, Any]]) -> int:
        """Delete network locations from their respective CIDs (optimized batch deletion)

        Args:
            locations: List of location dictionaries to delete (with _cid tag)

        Returns:
            Number of successfully deleted locations
        """
        if not locations:
            return 0

        print_info(f"Deleting {len(locations)} Network Locations...")
        success_count = 0
        total = len(locations)

        # Group locations by CID for efficient batch deletion
        locs_by_cid = {}
        for loc in locations:
            cid = loc.get('_cid')
            if cid not in locs_by_cid:
                locs_by_cid[cid] = []
            locs_by_cid[cid].append(loc)

        # Process each CID
        processed = 0
        for cid, cid_locs in locs_by_cid.items():
            cid_name = self.cid_names.get(cid, cid[:12])

            # Create auth once per CID
            cid_auth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url,
                member_cid=cid
            )
            cid_auth.token()
            cid_fw = FirewallManagement(auth_object=cid_auth)

            # Delete in batches of 100 (API limit)
            batch_size = 100
            for i in range(0, len(cid_locs), batch_size):
                batch = cid_locs[i:i + batch_size]
                batch_ids = [loc.get('id') for loc in batch]

                # Show progress
                progress_pct = (processed / total) * 100
                print(f"\r  Progress: {processed}/{total} ({progress_pct:.0f}%) - {cid_name[:30]:<30}", end='', flush=True)

                response = cid_fw.delete_network_locations(ids=batch_ids)

                if response['status_code'] in [200, 201]:
                    success_count += len(batch_ids)
                    processed += len(batch_ids)
                else:
                    # If batch fails, try individual deletions
                    for loc in batch:
                        single_response = cid_fw.delete_network_locations(ids=loc.get('id'))
                        if single_response['status_code'] in [200, 201]:
                            success_count += 1
                        processed += 1

        print()  # New line after progress
        print_success(f"✓ Deleted {success_count} Network Locations")
        return success_count


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Clean up test Firewall Management data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (with confirmation)
  python cleanup_test_data.py --config ../config/credentials.json

  # Non-interactive mode (auto-confirm)
  python cleanup_test_data.py --yes

  # Dry run (show what would be deleted)
  python cleanup_test_data.py --dry-run
        """
    )

    # Credential arguments
    parser.add_argument('--config', type=str, help='Path to credentials JSON file')
    parser.add_argument('--client-id', type=str, help='CrowdStrike API Client ID')
    parser.add_argument('--client-secret', type=str, help='CrowdStrike API Client Secret')
    parser.add_argument('--base-url', type=str, default='https://api.crowdstrike.com',
                       help='API base URL (default: US-1)')

    # Mode arguments
    parser.add_argument('--yes', action='store_true',
                       help='Auto-confirm deletion (no prompts)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')

    args = parser.parse_args()

    # Print logo and header
    print_jg_logo()
    print_header("FIREWALL TEST DATA CLEANUP")
    print()

    if args.dry_run:
        print_warning("⚠️  DRY RUN MODE - No resources will be deleted")
        print()

    # Get credentials
    try:
        config_path = args.config or '../config/credentials.json'

        client_id, client_secret, base_url, source = get_credentials_smart(
            config_path=config_path,
            client_id=args.client_id,
            client_secret=args.client_secret,
            base_url=args.base_url
        )

        if not client_id or not client_secret:
            print_error("No credentials found. Please provide:")
            print_error("  1. --config path/to/credentials.json")
            print_error("  2. --client-id and --client-secret")
            print_error("  3. Environment variables FALCON_CLIENT_ID and FALCON_CLIENT_SECRET")
            sys.exit(1)

    except Exception as e:
        print_error(f"Failed to load credentials: {e}")
        sys.exit(1)

    # Initialize cleanup tool
    try:
        cleanup = TestDataCleanup(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
    except Exception as e:
        print_error(f"Failed to initialize: {e}")
        sys.exit(1)

    print()

    # Get Child CIDs
    print_section("RETRIEVING CHILD CIDs")
    print()

    try:
        child_cids = cleanup.get_child_cids()

        if not child_cids:
            print_warning("No Child CIDs found. Nothing to clean.")
            sys.exit(0)

    except Exception as e:
        print_error(f"Failed to retrieve Child CIDs: {e}")
        sys.exit(1)

    print()

    # Scan for test data in all Child CIDs
    print_section("SCANNING FOR TEST DATA IN CHILD CIDs")
    print()

    test_policies = []
    test_rule_groups = []
    test_locations = []

    for child_cid_info in child_cids:
        child_cid = child_cid_info['cid']
        child_name = child_cid_info['name']

        print_info(f"Scanning: {child_name}")

        try:
            test_policies.extend(cleanup.find_test_policies(child_cid))
            test_rule_groups.extend(cleanup.find_test_rule_groups(child_cid))
            test_locations.extend(cleanup.find_test_network_locations(child_cid))
        except Exception as e:
            print_error(f"  Failed to scan {child_name}: {e}")
            continue

        print()

    total_resources = len(test_policies) + len(test_rule_groups) + len(test_locations)

    print()

    if total_resources == 0:
        print_success("✓ No test data found. Environment is clean!")
        sys.exit(0)

    # Display summary
    print_section("RESOURCES TO DELETE")
    print()

    if test_policies:
        print_info(f"Policies ({len(test_policies)}):")
        for policy in test_policies:
            enabled_status = "✓ Enabled" if policy.get('enabled') else "⊗ Disabled"
            cid_name = cleanup.cid_names.get(policy.get('_cid'), 'Unknown')
            print_info(f"  - [{cid_name}] {policy.get('name')} [{enabled_status}]")
        print()

    if test_rule_groups:
        print_info(f"Rule Groups ({len(test_rule_groups)}):")
        for rg in test_rule_groups:
            enabled_status = "✓ Enabled" if rg.get('enabled') else "⊗ Disabled"
            rule_count = len(rg.get('rules', []))
            cid_name = cleanup.cid_names.get(rg.get('_cid'), 'Unknown')
            print_info(f"  - [{cid_name}] {rg.get('name')} [{enabled_status}] - {rule_count} rules")
        print()

    if test_locations:
        print_info(f"Network Locations ({len(test_locations)}):")
        for loc in test_locations:
            enabled_status = "✓ Enabled" if loc.get('enabled') else "⊗ Disabled"
            cid_name = cleanup.cid_names.get(loc.get('_cid'), 'Unknown')
            print_info(f"  - [{cid_name}] {loc.get('name')} [{enabled_status}]")
        print()

    print_warning(f"⚠️  Total: {total_resources} resource(s) will be deleted from Child CIDs")
    print_info("⚠️  PARENT CID will NOT be affected")
    print()

    # Confirm deletion
    if not args.yes and not args.dry_run:
        print_warning("This action cannot be undone!")
        response = input("Are you sure you want to delete these resources? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print_info("Cleanup cancelled.")
            sys.exit(0)
        print()

    if args.dry_run:
        print_info("Dry run complete. No resources were deleted.")
        sys.exit(0)

    # Delete resources (in correct order: Policies -> Rule Groups -> Network Locations)
    print_section("DELETING RESOURCES")
    print()

    deleted_policies = cleanup.delete_policies(test_policies)
    print()

    deleted_rule_groups = cleanup.delete_rule_groups(test_rule_groups)
    print()

    deleted_locations = cleanup.delete_network_locations(test_locations)
    print()

    # Summary
    print_section("CLEANUP COMPLETE")
    print_success(f"✓ Deleted {deleted_policies} Policies")
    print_success(f"✓ Deleted {deleted_rule_groups} Rule Groups")
    print_success(f"✓ Deleted {deleted_locations} Network Locations")
    print()

    total_deleted = deleted_policies + deleted_rule_groups + deleted_locations
    if total_deleted == total_resources:
        print_success("✓ All test data successfully deleted!")
    else:
        print_warning(f"⚠️  Some deletions failed. Deleted {total_deleted}/{total_resources} resources")


if __name__ == "__main__":
    main()

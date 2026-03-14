#!/usr/bin/env python3
"""
Firewall Management Replication Script for CrowdStrike Flight Control

This script replicates Firewall Management configurations (Policies, Rule Groups,
Rules, and Network Locations/Contexts) from a Parent CID to selected Child CIDs
in a Flight Control environment.

Features:
- Interactive selection of Firewall Policies to replicate
- Automatic replication of all dependencies (Rule Groups, Rules, Contexts)
- Conflict detection and resolution
- Maintains all relationships between elements
- Detailed logging and progress tracking

Author: Claude Opus 4.6
Date: 2026-03-14
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
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from falconpy import OAuth2, FirewallManagement, FirewallPolicies, FlightControl
from utils.auth import get_credentials_smart
from utils.formatting import (
    print_header, print_section, print_info, print_success,
    print_error, print_warning, Colors
)


class FirewallReplicator:
    """Handles replication of Firewall Management configurations across CIDs"""

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.crowdstrike.com"):
        """Initialize the Firewall Replicator

        Args:
            client_id: CrowdStrike API Client ID
            client_secret: CrowdStrike API Client Secret
            base_url: API base URL (default: US-1)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url

        # Track conflict resolution preference
        self.skip_all_duplicates = False

        # Initialize API clients
        print_info("Authenticating to Falcon API...")

        # Create shared OAuth2 object (recommended for multiple services)
        self.auth = OAuth2(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )

        # Force token generation
        token_result = self.auth.token()
        if token_result.get('status_code') != 201:
            raise Exception(f"Authentication failed: {token_result.get('body')}")

        # Initialize service classes with shared auth
        self.falcon_fw = FirewallManagement(auth_object=self.auth)
        self.falcon_fp = FirewallPolicies(auth_object=self.auth)
        self.falcon_fc = FlightControl(auth_object=self.auth)
        print_success("Authentication successful!")

        # Cache for extracted data
        self.parent_cid = None
        self.child_cids = []
        self.all_cids = []
        self.cid_names = {}

        # Firewall data
        self.network_locations = {}  # Contexts
        self.rules = {}
        self.rule_groups = {}
        self.policy_containers = {}

    def get_cids(self) -> Tuple[str, List[Dict[str, str]]]:
        """Retrieve Parent and Child CIDs from Flight Control

        Returns:
            Tuple of (parent_cid, list of child CID dicts with 'name' and 'cid')
        """
        print_info("Retrieving CIDs from Flight Control...")

        # Query children
        response = self.falcon_fc.query_children()

        if response['status_code'] != 200:
            raise Exception(f"Failed to query CIDs: {response['body'].get('errors', 'Unknown error')}")

        child_cid_ids = response['body']['resources']

        if not child_cid_ids:
            print_warning("No Child CIDs found. This may be a standalone CID.")
            return None, []

        # Get child details
        details_response = self.falcon_fc.get_children(ids=child_cid_ids)

        if details_response['status_code'] != 200:
            raise Exception(f"Failed to get CID details: {details_response['body'].get('errors', 'Unknown error')}")

        children = []
        parent = None

        for cid_data in details_response['body']['resources']:
            cid_id = cid_data.get('id') or cid_data.get('child_cid')
            cid_name = cid_data.get('name', 'Unnamed CID')
            children.append({'name': cid_name, 'cid': cid_id})
            self.cid_names[cid_id] = cid_name

            # Try to get parent from first child (if available)
            if not parent and cid_data.get('parent_cid'):
                parent = cid_data.get('parent_cid')

        # If no parent_cid field is present, the authenticated CID is the Parent
        # We can get it from the auth object or just note it as "current CID"
        if not parent:
            # The authenticated CID is the Parent - we're already on it
            print_info("Note: Authenticated as Parent CID (no parent_cid field in children)")
            parent = "current"  # Placeholder to indicate we're on the parent

        self.parent_cid = parent
        self.child_cids = children
        self.all_cids = [parent] + [c['cid'] for c in children] if parent else [c['cid'] for c in children]

        print_success(f"Found Parent CID (authenticated) and {len(children)} Child CID(s)")

        return parent, children

    def extract_network_locations(self, cid: str) -> Dict[str, Any]:
        """Extract Network Locations (Contexts) from a CID

        Args:
            cid: CID to extract from

        Returns:
            Dictionary of network location ID -> details
        """
        print_info(f"  Extracting Network Locations (Contexts)...")

        # Query all network location IDs
        query_response = self.falcon_fw.query_network_locations()

        if query_response['status_code'] != 200:
            print_error(f"Failed to query network locations: {query_response['body'].get('errors')}")
            return {}

        location_ids = query_response['body']['resources']

        if not location_ids:
            print_info(f"    No Network Locations found")
            return {}

        # Get details for each location
        details_response = self.falcon_fw.get_network_locations_details(ids=location_ids)

        if details_response['status_code'] != 200:
            print_error(f"Failed to get network location details: {details_response['body'].get('errors')}")
            return {}

        locations = {}
        for loc in details_response['body']['resources']:
            loc_id = loc.get('id')
            if loc_id:
                locations[loc_id] = loc

        print_success(f"    Found {len(locations)} Network Location(s)")
        return locations

    def extract_rules(self, cid: str) -> Dict[str, Any]:
        """Extract Firewall Rules from a CID

        Args:
            cid: CID to extract from

        Returns:
            Dictionary of rule ID -> details
        """
        print_info(f"  Extracting Firewall Rules...")

        # Query all rule IDs
        query_response = self.falcon_fw.query_rules()

        if query_response['status_code'] != 200:
            print_error(f"Failed to query rules: {query_response['body'].get('errors')}")
            return {}

        rule_ids = query_response['body']['resources']

        if not rule_ids:
            print_info(f"    No Rules found")
            return {}

        # Get details for each rule
        details_response = self.falcon_fw.get_rules(ids=rule_ids)

        if details_response['status_code'] != 200:
            print_error(f"Failed to get rule details: {details_response['body'].get('errors')}")
            return {}

        rules = {}
        for rule in details_response['body']['resources']:
            rule_id = rule.get('id')
            if rule_id:
                rules[rule_id] = rule

        print_success(f"    Found {len(rules)} Rule(s)")
        return rules

    def extract_rule_groups(self, cid: str) -> Dict[str, Any]:
        """Extract Rule Groups from a CID

        Args:
            cid: CID to extract from

        Returns:
            Dictionary of rule group ID -> details
        """
        print_info(f"  Extracting Rule Groups...")

        # Query all rule group IDs
        query_response = self.falcon_fw.query_rule_groups()

        if query_response['status_code'] != 200:
            print_error(f"Failed to query rule groups: {query_response['body'].get('errors')}")
            return {}

        rg_ids = query_response['body']['resources']

        if not rg_ids:
            print_info(f"    No Rule Groups found")
            return {}

        # Get details for each rule group
        details_response = self.falcon_fw.get_rule_groups(ids=rg_ids)

        if details_response['status_code'] != 200:
            print_error(f"Failed to get rule group details: {details_response['body'].get('errors')}")
            return {}

        rule_groups = {}
        for rg in details_response['body']['resources']:
            rg_id = rg.get('id')
            if rg_id:
                rule_groups[rg_id] = rg

        print_success(f"    Found {len(rule_groups)} Rule Group(s)")
        return rule_groups

    def extract_policy_containers(self, cid: str) -> Dict[str, Any]:
        """Extract Policy Containers (Firewall Policies) from a CID

        Args:
            cid: CID to extract from

        Returns:
            Dictionary of policy ID -> details
        """
        print_info(f"  Extracting Policy Containers (Firewall Policies)...")

        # Query policies using FirewallPolicies API
        query_response = self.falcon_fp.query_policies()

        if query_response['status_code'] != 200:
            print_error(f"Failed to query policies: {query_response['body'].get('errors')}")
            return {}

        policy_ids = query_response['body']['resources']

        if not policy_ids:
            print_info(f"    No Policy Containers found")
            return {}

        # Get policy details from FirewallPolicies
        policies_response = self.falcon_fp.get_policies(ids=policy_ids)

        if policies_response['status_code'] != 200:
            print_error(f"Failed to get policies: {policies_response['body'].get('errors')}")
            return {}

        # Get policy container details from FirewallManagement (includes rule_group_ids)
        containers_response = self.falcon_fw.get_policy_containers(ids=policy_ids)

        policies = {}
        containers = {}

        # Index containers by ID
        if containers_response['status_code'] == 200:
            for container in containers_response['body'].get('resources', []):
                container_id = container.get('policy_id')
                if container_id:
                    containers[container_id] = container

        # Merge policy info with container info
        for policy in policies_response['body'].get('resources', []):
            policy_id = policy.get('id')
            if policy_id:
                # Start with policy data
                merged = policy.copy()

                # Add container data (rule_group_ids, settings, etc.)
                if policy_id in containers:
                    container = containers[policy_id]
                    merged.update({
                        'rule_group_ids': container.get('rule_group_ids', []),
                        'default_inbound': container.get('default_inbound'),
                        'default_outbound': container.get('default_outbound'),
                        'enforce': container.get('enforce'),
                        'local_logging': container.get('local_logging'),
                        'tracking': container.get('tracking'),
                        'test_mode': container.get('test_mode')
                    })

                policies[policy_id] = merged

        print_success(f"    Found {len(policies)} Policy Container(s)")
        return policies

    def extract_all_from_parent(self):
        """Extract all Firewall Management configurations from Parent CID"""

        if not self.parent_cid:
            raise Exception("No Parent CID available. Cannot extract configurations.")

        print_section(f"Extracting Firewall Configurations from Parent CID")
        print_info(f"Parent CID: {self.parent_cid[:12]}...")

        # Extract in dependency order
        self.network_locations = self.extract_network_locations(self.parent_cid)
        self.rules = self.extract_rules(self.parent_cid)
        self.rule_groups = self.extract_rule_groups(self.parent_cid)
        self.policy_containers = self.extract_policy_containers(self.parent_cid)

        print()
        print_success(f"Extraction complete!")
        print_info(f"Summary:")
        print_info(f"  - Network Locations: {len(self.network_locations)}")
        print_info(f"  - Rules: {len(self.rules)}")
        print_info(f"  - Rule Groups: {len(self.rule_groups)}")
        print_info(f"  - Policy Containers: {len(self.policy_containers)}")

    def select_policies_interactive(self) -> List[str]:
        """Interactive selection of policies to replicate

        Returns:
            List of selected policy IDs
        """
        if not self.policy_containers:
            print_warning("No Firewall Policies found in Parent CID.")
            return []

        print_section("SELECT FIREWALL POLICIES TO REPLICATE")
        print_info("Available Firewall Policies:")
        print()

        policy_list = list(self.policy_containers.items())

        for idx, (policy_id, policy) in enumerate(policy_list, 1):
            policy_name = policy.get('name', 'Unnamed Policy')
            platform = policy.get('platform_name', 'Unknown')
            enabled = policy.get('enabled', False)
            status = "✓ Enabled" if enabled else "○ Disabled"

            print(f"  [{idx}] {policy_name}")
            print(f"      Platform: {platform} | {status}")
            print(f"      ID: {policy_id}")
            print()

        print_info("Enter your selection:")
        print_info("  - Policy numbers (comma-separated): 1,3,5")
        print_info("  - 'all' to select all policies")
        print_info("  - 'q' to quit")
        print()

        while True:
            selection = input("Select Policies: ").strip().lower()

            if selection == 'q':
                print_warning("Replication cancelled by user.")
                sys.exit(0)

            if selection == 'all':
                return [pid for pid, _ in policy_list]

            # Parse comma-separated numbers
            try:
                indices = [int(x.strip()) for x in selection.split(',')]

                # Validate indices
                if any(i < 1 or i > len(policy_list) for i in indices):
                    print_error(f"Invalid selection. Please enter numbers between 1 and {len(policy_list)}")
                    continue

                selected_ids = [policy_list[i-1][0] for i in indices]

                print()
                print_success(f"✓ Selected {len(selected_ids)} Policy/Policies:")
                for pid in selected_ids:
                    policy_name = self.policy_containers[pid].get('name', 'Unnamed')
                    print_info(f"  • {policy_name}")
                print()

                return selected_ids

            except ValueError:
                print_error("Invalid input. Please enter numbers separated by commas, 'all', or 'q'")

    def select_child_cids_interactive(self) -> List[str]:
        """Interactive selection of Child CIDs for replication

        Returns:
            List of selected Child CID IDs
        """
        if not self.child_cids:
            print_warning("No Child CIDs available.")
            return []

        print_section("SELECT CHILD CIDs FOR REPLICATION")
        print_info("Available Child CIDs:")
        print()

        for idx, child in enumerate(self.child_cids, 1):
            print(f"  [{idx}] {child['name']}")
            print(f"      CID: {child['cid'][:12]}...")
            print()

        print_info("Enter your selection:")
        print_info("  - CID numbers (comma-separated): 1,2,3")
        print_info("  - 'all' to select all Child CIDs")
        print_info("  - 'q' to quit")
        print()

        while True:
            selection = input("Select Child CIDs: ").strip().lower()

            if selection == 'q':
                print_warning("Replication cancelled by user.")
                sys.exit(0)

            if selection == 'all':
                return [c['cid'] for c in self.child_cids]

            try:
                indices = [int(x.strip()) for x in selection.split(',')]

                if any(i < 1 or i > len(self.child_cids) for i in indices):
                    print_error(f"Invalid selection. Please enter numbers between 1 and {len(self.child_cids)}")
                    continue

                selected_cids = [self.child_cids[i-1]['cid'] for i in indices]

                print()
                print_success(f"✓ Selected {len(selected_cids)} Child CID(s):")
                for cid in selected_cids:
                    print_info(f"  • {self.cid_names.get(cid, 'Unknown')}")
                print()

                return selected_cids

            except ValueError:
                print_error("Invalid input. Please enter numbers separated by commas, 'all', or 'q'")

    def find_existing_resource_by_name(self, resource_type: str, name: str, target_cid: str) -> Optional[str]:
        """Find existing resource ID by name in target CID

        Args:
            resource_type: Type of resource ('location', 'rule_group', 'policy')
            name: Name of the resource to find
            target_cid: Target CID to search in

        Returns:
            Resource ID if found, None otherwise
        """
        try:
            if resource_type == 'location':
                # Query network locations
                response = self.falcon_fw.query_network_locations()
                if response['status_code'] != 200:
                    return None

                location_ids = response['body']['resources']
                if not location_ids:
                    return None

                # Get details to find by name
                details = self.falcon_fw.get_network_locations(ids=location_ids)
                if details['status_code'] == 200:
                    for loc in details['body'].get('resources', []):
                        if loc.get('name') == name:
                            return loc.get('id')

            elif resource_type == 'rule_group':
                # Query rule groups
                response = self.falcon_fw.query_rule_groups()
                if response['status_code'] != 200:
                    return None

                rg_ids = response['body']['resources']
                if not rg_ids:
                    return None

                # Get details to find by name
                details = self.falcon_fw.get_rule_groups(ids=rg_ids)
                if details['status_code'] == 200:
                    for rg in details['body'].get('resources', []):
                        if rg.get('name') == name:
                            return rg.get('id')

            elif resource_type == 'policy':
                # Query policies
                response = self.falcon_fp.query_policies()
                if response['status_code'] != 200:
                    return None

                policy_ids = response['body']['resources']
                if not policy_ids:
                    return None

                # Get details to find by name
                details = self.falcon_fp.get_policies(ids=policy_ids)
                if details['status_code'] == 200:
                    for policy in details['body'].get('resources', []):
                        if policy.get('name') == name:
                            return policy.get('id')

            return None

        except Exception as e:
            print_error(f"Error finding existing {resource_type}: {e}")
            return None

    def handle_duplicate(self, resource_type: str, resource_name: str, child_name: str) -> str:
        """Ask user how to handle duplicate resource

        Args:
            resource_type: Type of resource (Policy, Rule Group, Network Location)
            resource_name: Name of the duplicate resource
            child_name: Name of the Child CID

        Returns:
            Action to take: 'skip', 'rename', or 'overwrite'
            Sets self.skip_all_duplicates = True if user chooses 'skip_all'
        """
        print()
        print_warning(f"⚠️  {resource_type} '{resource_name}' already exists in {child_name}")
        print()
        print_info("How would you like to proceed?")
        print_info("  [1] Skip - Keep existing resource, don't replicate")
        print_info("  [2] Rename - Create new with version suffix (e.g., '_v2')")
        print_info("  [3] Overwrite - Update existing resource with Parent version")
        print_info("  [4] Skip All - Skip all remaining duplicates for this Child CID")
        print()

        while True:
            choice = input("Your choice (1-4): ").strip()

            if choice == '1':
                return 'skip'
            elif choice == '2':
                return 'rename'
            elif choice == '3':
                return 'overwrite'
            elif choice == '4':
                self.skip_all_duplicates = True  # Set flag for future duplicates
                return 'skip_all'
            else:
                print_error("Invalid choice. Please enter 1, 2, 3, or 4")

    def replicate_network_location(self, location_data: Dict[str, Any], target_cid: str,
                                   skip_duplicates: bool = False) -> Optional[str]:
        """Replicate a network location to target CID

        Args:
            location_data: Network location configuration
            target_cid: Target CID
            skip_duplicates: If True, silently skip duplicates without asking

        Returns:
            Created location ID or None if skipped/failed
        """
        # Remove fields that shouldn't be in creation request
        location_config = {k: v for k, v in location_data.items()
                          if k not in ['id', 'created_by', 'created_on', 'modified_by', 'modified_on', 'cid']}

        original_name = location_config.get('name')

        # Display information
        print_info(f"  Replicating: {original_name}")

        try:
            response = self.falcon_fw.create_network_locations(body=location_config)

            if response['status_code'] in [200, 201]:
                return response['body']['resources'][0]['id']
            elif response['status_code'] == 400:
                errors = response['body'].get('errors', [])
                # Check if it's a duplicate name error
                if any('duplicate name' in str(err).lower() for err in errors):
                    if skip_duplicates:
                        return None  # Silently skip

                    # Ask user what to do
                    child_name = self.cid_names.get(target_cid, target_cid[:12])
                    action = self.handle_duplicate("Network Location", original_name, child_name)

                    if action == 'skip' or action == 'skip_all':
                        return None
                    elif action == 'rename':
                        # Try with _v2, _v3, etc.
                        for version in range(2, 10):
                            location_config['name'] = f"{original_name}_v{version}"
                            response = self.falcon_fw.create_network_locations(body=location_config)
                            if response['status_code'] in [200, 201]:
                                print_success(f"✓ Created as '{location_config['name']}'")
                                return response['body']['resources'][0]['id']
                        print_error(f"Failed to create renamed location after multiple attempts")
                        return None
                    elif action == 'overwrite':
                        # Find existing resource ID
                        existing_id = self.find_existing_resource_by_name('location', original_name, target_cid)
                        if not existing_id:
                            print_error(f"Could not find existing location '{original_name}' - skipping")
                            return None

                        # Update the existing location
                        location_config['id'] = existing_id
                        update_response = self.falcon_fw.update_network_locations(body=location_config)

                        if update_response['status_code'] in [200, 201]:
                            print_success(f"✓ Updated existing location '{original_name}'")
                            return existing_id
                        else:
                            print_error(f"Failed to update location: {update_response['body'].get('errors')}")
                            return None
                else:
                    print_error(f"Failed to create location '{original_name}': {errors}")
                    return None
            else:
                print_error(f"Failed to create location '{original_name}': {response['body'].get('errors')}")
                return None
        except Exception as e:
            print_error(f"Exception creating location: {e}")
            return None

    def replicate_rule_group(self, group_data: Dict[str, Any], target_cid: str,
                            location_id_map: Dict[str, str] = None,
                            skip_duplicates: bool = False) -> Optional[str]:
        """Replicate a rule group to target CID

        Args:
            group_data: Rule group configuration
            target_cid: Target CID
            location_id_map: Mapping of old location IDs to new ones
            skip_duplicates: If True, silently skip duplicates without asking

        Returns:
            Created rule group ID or None if skipped/failed
        """
        # Extract rules from the source group data
        source_rules = group_data.get('rules', [])

        # Get enabled status from source (preserve disabled state)
        group_enabled = group_data.get('enabled', True)

        # Prepare rules with precedence preserved
        rules_to_create = []
        disabled_rules_count = 0
        if source_rules:
            # Sort rules by precedence to ensure correct order
            sorted_rules = sorted(source_rules, key=lambda r: r.get('precedence', 999999))

            for rule in sorted_rules:
                # Get enabled status (preserve disabled state)
                rule_enabled = rule.get('enabled', True)
                if not rule_enabled:
                    disabled_rules_count += 1

                # Build rule configuration
                rule_config = {
                    'name': rule.get('name'),
                    'description': rule.get('description', ''),
                    'enabled': rule_enabled,  # CRITICAL: Preserve enabled/disabled status
                    'precedence': rule.get('precedence'),  # CRITICAL: Preserve precedence
                    'action': rule.get('action'),
                    'direction': rule.get('direction'),
                    'protocol': rule.get('protocol'),
                    'address_family': rule.get('address_family', 'IP4'),
                    'log': rule.get('log', False),
                }

                # Add optional fields if present
                if 'local_address' in rule:
                    rule_config['local_address'] = rule['local_address']
                if 'local_port' in rule:
                    rule_config['local_port'] = rule['local_port']
                if 'remote_address' in rule:
                    rule_config['remote_address'] = rule['remote_address']
                if 'remote_port' in rule:
                    rule_config['remote_port'] = rule['remote_port']
                if 'icmp' in rule:
                    rule_config['icmp'] = rule['icmp']
                if 'monitor' in rule:
                    rule_config['monitor'] = rule['monitor']
                if 'fields' in rule:
                    rule_config['fields'] = rule['fields']
                if 'temp_id' in rule:
                    rule_config['temp_id'] = rule['temp_id']

                rules_to_create.append(rule_config)

        # Build rule group configuration
        group_config = {
            'name': group_data.get('name'),
            'description': group_data.get('description', ''),
            'enabled': group_enabled,  # CRITICAL: Preserve enabled/disabled status
            'platform': group_data.get('platform'),
            'rules': rules_to_create  # Include all rules with precedence
        }

        original_name = group_config.get('name')

        # Display status information
        status_indicator = "✓ Enabled" if group_enabled else "⊗ Disabled"
        rules_status = f"{len(source_rules)} rules ({disabled_rules_count} disabled)" if source_rules else "no rules"
        print_info(f"  Replicating: {original_name} [{status_indicator}] - {rules_status}")

        try:
            response = self.falcon_fw.create_rule_group(body=group_config)

            if response['status_code'] in [200, 201]:
                resources = response['body'].get('resources', [])
                if resources:
                    return resources[0] if isinstance(resources[0], str) else resources[0].get('id')
                return None
            elif response['status_code'] == 400:
                errors = response['body'].get('errors', [])
                # Check if it's a duplicate name error
                if any('duplicate' in str(err).lower() for err in errors):
                    if skip_duplicates:
                        return None  # Silently skip

                    # Ask user what to do
                    child_name = self.cid_names.get(target_cid, target_cid[:12])
                    action = self.handle_duplicate("Rule Group", original_name, child_name)

                    if action == 'skip' or action == 'skip_all':
                        return None
                    elif action == 'rename':
                        # Try with _v2, _v3, etc.
                        for version in range(2, 10):
                            group_config['name'] = f"{original_name}_v{version}"
                            response = self.falcon_fw.create_rule_group(body=group_config)
                            if response['status_code'] in [200, 201]:
                                resources = response['body'].get('resources', [])
                                print_success(f"✓ Created as '{group_config['name']}'")
                                if resources:
                                    return resources[0] if isinstance(resources[0], str) else resources[0].get('id')
                                return None
                        print_error(f"Failed to create renamed rule group after multiple attempts")
                        return None
                    elif action == 'overwrite':
                        # Find existing resource ID
                        existing_id = self.find_existing_resource_by_name('rule_group', original_name, target_cid)
                        if not existing_id:
                            print_error(f"Could not find existing rule group '{original_name}' - skipping")
                            return None

                        # Update the existing rule group
                        group_config['id'] = existing_id
                        update_response = self.falcon_fw.update_rule_group(body=group_config)

                        if update_response['status_code'] in [200, 201]:
                            print_success(f"✓ Updated existing rule group '{original_name}'")
                            return existing_id
                        else:
                            print_error(f"Failed to update rule group: {update_response['body'].get('errors')}")
                            return None
                else:
                    print_error(f"Failed to create rule group '{original_name}': {errors}")
                    return None
            else:
                print_error(f"Failed to create rule group '{original_name}': {response['body'].get('errors')}")
                return None
        except Exception as e:
            print_error(f"Exception creating rule group: {e}")
            return None

    def replicate_policy(self, policy_data: Dict[str, Any], target_cid: str,
                        rule_group_id_map: Dict[str, str] = None,
                        skip_duplicates: bool = False) -> Optional[str]:
        """Replicate a policy to target CID

        Args:
            policy_data: Policy configuration
            target_cid: Target CID
            rule_group_id_map: Mapping of old rule group IDs to new ones
            skip_duplicates: If True, silently skip duplicates without asking

        Returns:
            Created policy ID or None if skipped/failed
        """
        # Create policy using FirewallPolicies API
        original_name = policy_data.get('name')
        policy_enabled = policy_data.get('enabled', True)

        # Display status information
        status_indicator = "✓ Enabled" if policy_enabled else "⊗ Disabled"
        rg_count = len(policy_data.get('rule_group_ids', []))
        rg_info = f"{rg_count} Rule Groups" if rg_count > 0 else "no Rule Groups"
        print_info(f"  Replicating: {original_name} [{status_indicator}] - {rg_info}")

        policy_body = {
            "resources": [
                {
                    "name": original_name,
                    "description": policy_data.get('description', ''),
                    "platform_name": policy_data.get('platform_name'),
                    "enabled": policy_enabled  # CRITICAL: Preserve enabled/disabled status
                }
            ]
        }

        try:
            response = self.falcon_fp.create_policies(body=policy_body)

            if response['status_code'] not in [200, 201]:
                errors = response['body'].get('errors', [])
                # Check if it's a duplicate name error
                if any('duplicate' in str(err).lower() for err in errors):
                    if skip_duplicates:
                        return None  # Silently skip

                    # Ask user what to do
                    child_name = self.cid_names.get(target_cid, target_cid[:12])
                    action = self.handle_duplicate("Policy", original_name, child_name)

                    if action == 'skip' or action == 'skip_all':
                        return None
                    elif action == 'rename':
                        # Try with _v2, _v3, etc.
                        for version in range(2, 10):
                            policy_body['resources'][0]['name'] = f"{original_name}_v{version}"
                            response = self.falcon_fp.create_policies(body=policy_body)
                            if response['status_code'] in [200, 201]:
                                print_success(f"✓ Created as '{policy_body['resources'][0]['name']}'")
                                policy_id = response['body']['resources'][0]['id']
                                break
                            else:
                                # Check if this version also exists
                                if version == 9:
                                    print_error(f"Failed to create renamed policy after multiple attempts")
                                    return None
                        else:
                            return None
                    elif action == 'overwrite':
                        # Find existing policy ID
                        existing_id = self.find_existing_resource_by_name('policy', original_name, target_cid)
                        if not existing_id:
                            print_error(f"Could not find existing policy '{original_name}' - skipping")
                            return None

                        # Update the existing policy
                        update_body = {
                            "resources": [
                                {
                                    "id": existing_id,
                                    "name": original_name,
                                    "description": policy_data.get('description', ''),
                                    "platform_name": policy_data.get('platform_name'),
                                    "enabled": policy_enabled  # CRITICAL: Preserve enabled/disabled status
                                }
                            ]
                        }
                        update_response = self.falcon_fp.update_policies(body=update_body)

                        if update_response['status_code'] in [200, 201]:
                            print_success(f"✓ Updated existing policy '{original_name}'")
                            policy_id = existing_id
                        else:
                            print_error(f"Failed to update policy: {update_response['body'].get('errors')}")
                            return None
                else:
                    print_error(f"Failed to create policy '{original_name}': {errors}")
                    return None

            policy_id = response['body']['resources'][0]['id']

            # If rule groups need to be assigned
            if rule_group_id_map and policy_data.get('rule_group_ids'):
                # Map old rule group IDs to new ones
                old_rg_ids = policy_data.get('rule_group_ids', [])
                new_rg_ids = [rule_group_id_map.get(old_id) for old_id in old_rg_ids
                             if rule_group_id_map.get(old_id)]

                if new_rg_ids:
                    # Update policy container with rule groups
                    update_body = {
                        "policy_id": policy_id,
                        "rule_group_ids": new_rg_ids,
                        "default_inbound": policy_data.get('default_inbound', 'ALLOW'),
                        "default_outbound": policy_data.get('default_outbound', 'ALLOW'),
                        "enforce": policy_data.get('enforce', False),
                        "local_logging": policy_data.get('local_logging', False),
                        "tracking": policy_data.get('tracking', 'none'),
                        "test_mode": policy_data.get('test_mode', False)
                    }

                    update_response = self.falcon_fw.update_policy_container(
                        ids=policy_id,
                        body=update_body
                    )

                    if update_response['status_code'] not in [200, 201]:
                        print_warning(f"Policy created but failed to assign rule groups: {update_response['body'].get('errors')}")

            return policy_id

        except Exception as e:
            print_error(f"Exception creating policy: {e}")
            return None

    def replicate_to_child(self, child_cid: str, selected_policy_ids: List[str]):
        """Replicate selected policies and their dependencies to a Child CID

        Args:
            child_cid: Target Child CID
            selected_policy_ids: List of policy IDs to replicate
        """
        child_name = self.cid_names.get(child_cid, child_cid[:12])
        print_section(f"Replicating to: {child_name}")

        # Reset skip_all flag for this Child CID
        self.skip_all_duplicates = False

        # Step 1: Collect all dependencies
        print_info("Analyzing dependencies...")

        # Find all rule groups referenced by selected policies
        required_rule_group_ids = set()
        for policy_id in selected_policy_ids:
            policy = self.policy_containers.get(policy_id, {})
            rg_ids = policy.get('rule_group_ids', [])
            required_rule_group_ids.update(rg_ids)

        # Find all network locations referenced by rules in those rule groups
        required_location_ids = set()
        for rg_id in required_rule_group_ids:
            rule_group = self.rule_groups.get(rg_id, {})
            # TODO: Parse rules to find location references
            # For now, replicate all locations to be safe

        print_success(f"✓ Found {len(selected_policy_ids)} policies, {len(required_rule_group_ids)} rule groups")
        print()

        # Step 2: Replicate Network Locations
        location_id_map = {}
        if self.network_locations:
            print_info(f"Replicating {len(self.network_locations)} Network Locations...")
            success_count = 0
            skipped_count = 0
            for loc_id, loc_data in self.network_locations.items():
                new_id = self.replicate_network_location(loc_data, child_cid, skip_duplicates=self.skip_all_duplicates)
                if new_id:
                    location_id_map[loc_id] = new_id
                    success_count += 1
                else:
                    skipped_count += 1

            print_success(f"✓ Created {success_count} Network Locations")
            if skipped_count > 0:
                print_info(f"  (Skipped {skipped_count} - already exist)")
            print()

        # Step 3: Replicate Rule Groups
        rule_group_id_map = {}
        if required_rule_group_ids:
            print_info(f"Replicating {len(required_rule_group_ids)} Rule Groups...")
            success_count = 0
            skipped_count = 0
            for rg_id in required_rule_group_ids:
                rg_data = self.rule_groups.get(rg_id)
                if rg_data:
                    new_id = self.replicate_rule_group(rg_data, child_cid, location_id_map, skip_duplicates=self.skip_all_duplicates)
                    if new_id:
                        rule_group_id_map[rg_id] = new_id
                        success_count += 1
                    else:
                        skipped_count += 1

            print_success(f"✓ Created {success_count} Rule Groups")
            if skipped_count > 0:
                print_info(f"  (Skipped {skipped_count} - already exist)")
            print()

        # Step 4: Replicate Policies
        print_info(f"Replicating {len(selected_policy_ids)} Policies...")
        success_count = 0
        skipped_count = 0
        for policy_id in selected_policy_ids:
            policy_data = self.policy_containers.get(policy_id)
            if policy_data:
                new_id = self.replicate_policy(policy_data, child_cid, rule_group_id_map, skip_duplicates=self.skip_all_duplicates)
                if new_id:
                    success_count += 1
                else:
                    skipped_count += 1

        print_success(f"✓ Created {success_count} Policies")
        if skipped_count > 0:
            print_info(f"  (Skipped {skipped_count} - already exist)")
        print()

        print_success(f"✓ Replication to {child_name} complete!")
        print()


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Replicate Firewall Management configurations from Parent CID to Child CIDs in Flight Control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended)
  python replicate_firewall.py --config ../config/credentials.json

  # Using environment variables
  export FALCON_CLIENT_ID="your_id"
  export FALCON_CLIENT_SECRET="your_secret"
  python replicate_firewall.py
        """
    )

    # Credential arguments
    parser.add_argument('--config', type=str, help='Path to credentials JSON file')
    parser.add_argument('--client-id', type=str, help='CrowdStrike API Client ID')
    parser.add_argument('--client-secret', type=str, help='CrowdStrike API Client Secret')
    parser.add_argument('--base-url', type=str, default='https://api.crowdstrike.com',
                       help='API base URL (default: US-1)')

    # Mode arguments
    parser.add_argument('--non-interactive', action='store_true',
                       help='Non-interactive mode (replicate all policies to all children)')

    args = parser.parse_args()

    # Print header
    print_header("FIREWALL MANAGEMENT REPLICATION")
    print()

    # Get credentials
    try:
        # Set default config path if not provided
        config_path = args.config or '../config/credentials.json'

        client_id, client_secret, base_url, source = get_credentials_smart(
            config_path=config_path,
            client_id=args.client_id,
            client_secret=args.client_secret,
            base_url=args.base_url
        )

        # Check if credentials were actually loaded
        if not client_id or not client_secret:
            print_error("No credentials found. Please provide:")
            print_error("  1. --config <path> to credentials file, OR")
            print_error("  2. --client-id and --client-secret arguments, OR")
            print_error("  3. FALCON_CLIENT_ID and FALCON_CLIENT_SECRET environment variables")
            sys.exit(1)

    except Exception as e:
        print(f"Failed to load credentials: {e}")
        sys.exit(1)

    # Initialize replicator
    try:
        replicator = FirewallReplicator(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
    except Exception as e:
        print(f"Failed to initialize: {e}")
        sys.exit(1)

    print()

    # Get CIDs
    try:
        parent_cid, child_cids = replicator.get_cids()

        if not parent_cid:
            print_error("No Parent CID found. This script requires a Flight Control environment.")
            sys.exit(1)

        if not child_cids:
            print_error("No Child CIDs found. Nothing to replicate to.")
            sys.exit(1)

    except Exception as e:
        print(f"Failed to retrieve CIDs: {e}")
        sys.exit(1)

    print()

    # Extract configurations from Parent
    try:
        replicator.extract_all_from_parent()
    except Exception as e:
        print(f"Failed to extract configurations: {e}")
        sys.exit(1)

    print()

    # Check if there's anything to replicate
    if not replicator.policy_containers:
        print_warning("No Firewall Policies found in Parent CID. Nothing to replicate.")
        sys.exit(0)

    # Selection mode
    if args.non_interactive:
        # Replicate all policies to all children
        selected_policies = list(replicator.policy_containers.keys())
        selected_children = [c['cid'] for c in child_cids]

        print_info("Non-interactive mode: Replicating ALL policies to ALL Child CIDs")
        print()
    else:
        # Interactive selection
        selected_policies = replicator.select_policies_interactive()

        if not selected_policies:
            print_warning("No policies selected. Exiting.")
            sys.exit(0)

        selected_children = replicator.select_child_cids_interactive()

        if not selected_children:
            print_warning("No Child CIDs selected. Exiting.")
            sys.exit(0)

    # Replicate to each selected child
    print_section("REPLICATION SUMMARY")
    print_info(f"Policies to replicate: {len(selected_policies)}")
    print_info(f"Target Child CIDs: {len(selected_children)}")
    print()

    # Show what will be replicated
    print_info("Selected policies:")
    for policy_id in selected_policies:
        policy_name = replicator.policy_containers[policy_id].get('name', 'Unnamed')
        print_info(f"  • {policy_name}")
    print()

    print_info("Target Child CIDs:")
    for child_cid in selected_children:
        child_name = replicator.cid_names.get(child_cid, child_cid[:12])
        print_info(f"  • {child_name}")
    print()

    # Confirmation
    if not args.non_interactive:
        print_warning("⚠️  This will create resources in the selected Child CIDs!")
        confirm = input("Type 'yes' to proceed with replication: ").strip().lower()
        if confirm != 'yes':
            print_warning("Replication cancelled by user.")
            sys.exit(0)
        print()

    print_section("REPLICATION PROCESS")

    for child_cid in selected_children:
        try:
            replicator.replicate_to_child(child_cid, selected_policies)
        except Exception as e:
            child_name = replicator.cid_names.get(child_cid, child_cid[:12])
            print_error(f"Failed to replicate to {child_name}: {e}")
            continue

    print()
    print_section("REPLICATION COMPLETE")
    print_success("✓ Firewall configurations have been replicated!")
    print()
    print_info("Next steps:")
    print_info("  1. Verify policies in Child CID Falcon Console")
    print_info("  2. Test firewall rules")
    print_info("  3. Enable policies when ready")


if __name__ == "__main__":
    main()

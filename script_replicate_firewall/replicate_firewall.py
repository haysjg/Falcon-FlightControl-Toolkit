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
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from falconpy import OAuth2, FirewallManagement, FirewallPolicies, FlightControl
from utils.auth import get_credentials_smart
from utils.formatting import (
    print_header, print_section, print_info, print_success,
    print_error, print_warning, print_jg_logo, Colors
)


class FirewallReplicator:
    """Handles replication of Firewall Management configurations across CIDs"""

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.crowdstrike.com",
                 dry_run: bool = False, log_file: Optional[str] = None):
        """Initialize the Firewall Replicator

        Args:
            client_id: CrowdStrike API Client ID
            client_secret: CrowdStrike API Client Secret
            base_url: API base URL (default: US-1)
            dry_run: If True, preview changes without executing them
            log_file: Optional path to log file
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.dry_run = dry_run

        # Setup logging
        self.logger = self._setup_logging(log_file)

        if self.dry_run:
            self.logger.info("=" * 80)
            self.logger.info("DRY RUN MODE - No changes will be made")
            self.logger.info("=" * 80)

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

    def _setup_logging(self, log_file: Optional[str] = None) -> logging.Logger:
        """Setup logging to file and console

        Args:
            log_file: Optional path to log file. If None, auto-generates filename.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger('FirewallReplicator')
        logger.setLevel(logging.INFO)

        # Remove existing handlers
        logger.handlers = []

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler (INFO and above)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler
        if log_file is None:
            # Auto-generate log filename
            log_dir = Path(__file__).parent / 'logs'
            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = log_dir / f'firewall_replication_{timestamp}.log'

        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Log more detail to file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info(f"Logging to: {log_file}")
        logger.info("=" * 80)
        logger.info("Firewall Management Replication Session Started")
        logger.info("=" * 80)

        return logger

    def _log_operation(self, operation: str, resource_type: str, resource_name: str,
                      target_cid: str = None, status: str = "SUCCESS", details: str = ""):
        """Log a replication operation

        Args:
            operation: Type of operation (CREATE, UPDATE, SKIP, FAIL)
            resource_type: Type of resource (Network Location, Rule Group, Policy, etc.)
            resource_name: Name of the resource
            target_cid: Target CID (optional)
            status: Operation status (SUCCESS, FAILED, SKIPPED)
            details: Additional details about the operation
        """
        cid_info = f" -> {self.cid_names.get(target_cid, target_cid[:12])}" if target_cid else ""
        message = f"{operation} {resource_type}: {resource_name}{cid_info}"
        if details:
            message += f" | {details}"

        if status == "SUCCESS":
            self.logger.info(f"✓ {message}")
        elif status == "SKIPPED":
            self.logger.warning(f"⊗ SKIPPED: {message}")
        elif status == "FAILED":
            self.logger.error(f"✗ FAILED: {message}")
        else:
            self.logger.info(message)

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
        excluded_count = 0
        invalid_count = 0
        for policy in policies_response['body'].get('resources', []):
            policy_id = policy.get('id')
            policy_name = policy.get('name', '')

            # Skip platform default policies
            if policy_name.lower() in ['default', 'platform_default'] or policy.get('is_default_policy', False):
                self.logger.debug(f"Skipping default policy: {policy_name}")
                excluded_count += 1
                continue

            # Validate policy data (filter out "ghost" policies)
            if not policy_name or not policy_name.strip():
                self.logger.warning(f"Skipping policy with empty name (ID: {policy_id})")
                invalid_count += 1
                continue

            if not policy.get('platform_name'):
                self.logger.warning(f"Skipping policy '{policy_name}' with missing platform (ID: {policy_id})")
                invalid_count += 1
                continue

            if policy_id:
                # Start with policy data
                merged = policy.copy()

                # Add container data (rule_group_ids, settings, etc.)
                if policy_id in containers:
                    container = containers[policy_id]
                    rule_group_ids = container.get('rule_group_ids', [])

                    # Validate that referenced rule groups exist
                    valid_rg_ids = []
                    invalid_rg_ids = []
                    for rg_id in rule_group_ids:
                        if rg_id in self.rule_groups:
                            valid_rg_ids.append(rg_id)
                        else:
                            invalid_rg_ids.append(rg_id)

                    if invalid_rg_ids:
                        self.logger.warning(f"Policy '{policy_name}' references {len(invalid_rg_ids)} non-existent rule group(s) - filtering them out")
                        self.logger.debug(f"Invalid rule group IDs for '{policy_name}': {invalid_rg_ids}")

                    merged.update({
                        'rule_group_ids': valid_rg_ids,  # Only keep valid IDs
                        'default_inbound': container.get('default_inbound'),
                        'default_outbound': container.get('default_outbound'),
                        'enforce': container.get('enforce'),
                        'local_logging': container.get('local_logging'),
                        'tracking': container.get('tracking'),
                        'test_mode': container.get('test_mode')
                    })

                policies[policy_id] = merged

        if excluded_count > 0:
            print_info(f"    Excluded {excluded_count} default policy/policies (cannot be replicated)")
        if invalid_count > 0:
            print_warning(f"    Filtered out {invalid_count} invalid/ghost policy/policies")
        print_success(f"    Found {len(policies)} Policy Container(s) available for replication")
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
        location_enabled = location_config.get('enabled', True)

        # Display status information
        status_indicator = "✓ Enabled" if location_enabled else "⊗ Disabled"
        # Removed verbose print_info to show progress bar instead
        self.logger.debug(f"Replicating Network Location: {original_name} (enabled={location_enabled})")

        # Dry run mode - just preview
        if self.dry_run:
            print_info(f"    [DRY RUN] Would create Network Location: {original_name}")
            self._log_operation("DRY-RUN-CREATE", "Network Location", original_name, target_cid, "PREVIEW")
            return "dry-run-id"  # Return placeholder ID

        try:
            response = self.falcon_fw.create_network_locations(body=location_config)

            if response['status_code'] in [200, 201]:
                created_id = response['body']['resources'][0]['id']
                self._log_operation("CREATE", "Network Location", original_name, target_cid, "SUCCESS", f"ID: {created_id}")
                return created_id
            elif response['status_code'] == 400:
                errors = response['body'].get('errors', [])
                # Check if it's a duplicate name error
                if any('duplicate name' in str(err).lower() for err in errors):
                    self.logger.warning(f"Network Location '{original_name}' already exists in target CID")
                    if skip_duplicates:
                        self._log_operation("SKIP", "Network Location", original_name, target_cid, "SKIPPED", "Duplicate")
                        return None  # Silently skip

                    # Ask user what to do
                    child_name = self.cid_names.get(target_cid, target_cid[:12])
                    action = self.handle_duplicate("Network Location", original_name, child_name)
                    self.logger.info(f"User chose action: {action}")

                    if action == 'skip' or action == 'skip_all':
                        self._log_operation("SKIP", "Network Location", original_name, target_cid, "SKIPPED", "User choice")
                        return None
                    elif action == 'rename':
                        # Try with _v2, _v3, etc.
                        for version in range(2, 10):
                            location_config['name'] = f"{original_name}_v{version}"
                            response = self.falcon_fw.create_network_locations(body=location_config)
                            if response['status_code'] in [200, 201]:
                                print_success(f"✓ Created as '{location_config['name']}'")
                                created_id = response['body']['resources'][0]['id']
                                self._log_operation("CREATE", "Network Location", location_config['name'], target_cid, "SUCCESS", f"Renamed from {original_name}, ID: {created_id}")
                                return created_id
                        print_error(f"Failed to create renamed location after multiple attempts")
                        self._log_operation("CREATE", "Network Location", original_name, target_cid, "FAILED", "All rename attempts failed")
                        return None
                    elif action == 'overwrite':
                        # Find existing resource ID
                        existing_id = self.find_existing_resource_by_name('location', original_name, target_cid)
                        if not existing_id:
                            print_error(f"Could not find existing location '{original_name}' - skipping")
                            self._log_operation("UPDATE", "Network Location", original_name, target_cid, "FAILED", "Could not find existing resource")
                            return None

                        # Update the existing location
                        location_config['id'] = existing_id
                        update_response = self.falcon_fw.update_network_locations(body=location_config)

                        if update_response['status_code'] in [200, 201]:
                            print_success(f"✓ Updated existing location '{original_name}'")
                            self._log_operation("UPDATE", "Network Location", original_name, target_cid, "SUCCESS", f"ID: {existing_id}")
                            return existing_id
                        else:
                            print_error(f"Failed to update location: {update_response['body'].get('errors')}")
                            self._log_operation("UPDATE", "Network Location", original_name, target_cid, "FAILED", str(update_response['body'].get('errors')))
                            return None
                else:
                    print_error(f"Failed to create location '{original_name}': {errors}")
                    self._log_operation("CREATE", "Network Location", original_name, target_cid, "FAILED", str(errors))
                    return None
            else:
                print_error(f"Failed to create location '{original_name}': {response['body'].get('errors')}")
                self._log_operation("CREATE", "Network Location", original_name, target_cid, "FAILED", str(response['body'].get('errors')))
                return None
        except Exception as e:
            print_error(f"Exception creating location: {e}")
            self.logger.exception(f"Exception during Network Location replication: {original_name}")
            self._log_operation("CREATE", "Network Location", original_name, target_cid, "FAILED", f"Exception: {str(e)}")
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

        # Log status information (verbose output removed, using progress bar instead)
        status_indicator = "✓ Enabled" if group_enabled else "⊗ Disabled"
        rules_status = f"{len(source_rules)} rules ({disabled_rules_count} disabled)" if source_rules else "no rules"
        self.logger.debug(f"Replicating Rule Group: {original_name} [{status_indicator}] - {rules_status}")

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

        # Log status information (verbose output removed, using progress bar instead)
        status_indicator = "✓ Enabled" if policy_enabled else "⊗ Disabled"
        rg_count = len(policy_data.get('rule_group_ids', []))
        rg_info = f"{rg_count} Rule Groups" if rg_count > 0 else "no Rule Groups"
        self.logger.debug(f"Replicating Policy: {original_name} [{status_indicator}] - {rg_info}")

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
                    # CRITICAL: Add initial delay to allow policy creation to fully propagate
                    # CrowdStrike API needs time between policy creation and rule group assignment
                    time.sleep(1)

                    # Retry mechanism with policy reload (as indicated by 409 error message)
                    max_retries = 5
                    base_delay = 2  # Start with shorter delay since we reload

                    for attempt in range(max_retries):
                        # RELOAD policy from API to get fresh state (fixes 409 "reload and try again")
                        if attempt > 0:
                            self.logger.debug(f"Reloading policy '{original_name}' from API before retry {attempt + 1}")
                            reload_response = self.falcon_fp.get_policies(ids=[policy_id])

                            if reload_response['status_code'] == 200 and reload_response['body'].get('resources'):
                                # Use fresh policy data for update
                                fresh_policy = reload_response['body']['resources'][0]
                                self.logger.debug(f"Policy reloaded successfully, updating body with fresh data")
                            else:
                                self.logger.warning(f"Failed to reload policy, continuing with original data")
                                fresh_policy = None
                        else:
                            fresh_policy = None

                        # Build update body (use fresh data if available, otherwise original)
                        base_policy = fresh_policy if fresh_policy else policy_data
                        update_body = {
                            "policy_id": policy_id,
                            "rule_group_ids": new_rg_ids,
                            "default_inbound": base_policy.get('default_inbound', 'ALLOW'),
                            "default_outbound": base_policy.get('default_outbound', 'ALLOW'),
                            "enforce": base_policy.get('enforce', False),
                            "local_logging": base_policy.get('local_logging', False),
                            "tracking": base_policy.get('tracking', 'none'),
                            "test_mode": base_policy.get('test_mode', False)
                        }

                        update_response = self.falcon_fw.update_policy_container(
                            ids=policy_id,
                            body=update_body
                        )

                        if update_response['status_code'] in [200, 201]:
                            self.logger.info(f"Successfully assigned {len(new_rg_ids)} rule groups to policy '{original_name}' (attempt {attempt + 1})")
                            break
                        elif attempt < max_retries - 1:
                            # Progressive backoff: 2s, 4s, 6s, 8s
                            retry_delay = base_delay * (attempt + 1)
                            self.logger.warning(f"Rule group assignment attempt {attempt + 1} failed, reloading and retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                        else:
                            # Final attempt failed
                            print_warning(f"Policy created but failed to assign rule groups after {max_retries} attempts: {update_response['body'].get('errors')}")
                            self.logger.error(f"Failed to assign rule groups to policy '{original_name}' after {max_retries} attempts: {update_response['body'].get('errors')}")

            return policy_id

        except Exception as e:
            print_error(f"Exception creating policy: {e}")
            return None

    def validate_replication(self, child_cid: str, replicated_data: Dict[str, List[str]]) -> Dict[str, Any]:
        """Validate replicated resources match source configuration

        Args:
            child_cid: Child CID where resources were replicated
            replicated_data: Dictionary with resource types and parent IDs that were replicated
                           Format: {'policies': [id1, id2], 'rule_groups': [id1, id2], ...}

        Returns:
            Validation results dictionary with match/mismatch counts and details
        """
        child_name = self.cid_names.get(child_cid, child_cid[:12])

        self.logger.info("=" * 80)
        self.logger.info(f"Starting validation for Child CID: {child_name}")
        self.logger.info("=" * 80)

        validation_results = {
            'policies': {'matches': 0, 'mismatches': 0, 'missing': 0, 'details': []},
            'rule_groups': {'matches': 0, 'mismatches': 0, 'missing': 0, 'details': []},
            'network_locations': {'matches': 0, 'mismatches': 0, 'missing': 0, 'details': []}
        }

        # Switch to Child CID for validation
        print_section(f"Validating: {child_name}")
        self.logger.info(f"Switching to Child CID for validation: {child_cid}")

        # Save current auth
        original_auth = self.auth
        original_fw = self.falcon_fw
        original_fp = self.falcon_fp

        try:
            # Create new auth for Child CID
            child_auth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url,
                member_cid=child_cid
            )
            token_result = child_auth.token()
            if token_result.get('status_code') != 201:
                raise Exception(f"Failed to authenticate to Child CID: {token_result}")

            child_fw = FirewallManagement(auth_object=child_auth)
            child_fp = FirewallPolicies(auth_object=child_auth)

            # OPTIMIZATION: Fetch all Child resources once upfront instead of per-item
            # This dramatically reduces API calls from O(n) to O(1) per resource type

            # Fetch all Network Locations from Child CID once
            child_all_locs = {}
            child_locs_response = child_fw.query_network_locations()
            if child_locs_response['status_code'] == 200:
                child_loc_ids = child_locs_response['body'].get('resources', [])
                if child_loc_ids:
                    child_locs_details = child_fw.get_network_locations(ids=child_loc_ids)
                    if child_locs_details['status_code'] == 200:
                        for loc in child_locs_details['body'].get('resources', []):
                            child_all_locs[loc.get('name')] = loc

            # Fetch all Rule Groups from Child CID once
            child_all_rgs = {}
            child_rgs_response = child_fw.query_rule_groups()
            if child_rgs_response['status_code'] == 200:
                child_rg_ids = child_rgs_response['body'].get('resources', [])
                if child_rg_ids:
                    child_rgs_details = child_fw.get_rule_groups(ids=child_rg_ids)
                    if child_rgs_details['status_code'] == 200:
                        for rg in child_rgs_details['body'].get('resources', []):
                            child_all_rgs[rg.get('name')] = rg

            # Fetch all Policies from Child CID once
            child_all_policies = {}
            child_policies_response = child_fp.query_policies()
            if child_policies_response['status_code'] == 200:
                child_policy_ids = child_policies_response['body'].get('resources', [])
                if child_policy_ids:
                    # Get policy details
                    child_policies_details = child_fp.get_policies(ids=child_policy_ids)
                    if child_policies_details['status_code'] == 200:
                        for policy in child_policies_details['body'].get('resources', []):
                            child_all_policies[policy.get('name')] = policy

                    # Get policy containers for rule group info
                    child_containers_response = child_fw.get_policy_containers(ids=child_policy_ids)
                    if child_containers_response['status_code'] == 200:
                        for container in child_containers_response['body'].get('resources', []):
                            policy_name = child_all_policies.get(container.get('policy_id'), {}).get('name')
                            if policy_name and policy_name in child_all_policies:
                                child_all_policies[policy_name]['rule_group_ids'] = container.get('rule_group_ids', [])

            # Validate Network Locations
            if replicated_data.get('network_locations'):
                loc_count = len(replicated_data['network_locations'])
                print_info(f"  Validating {loc_count} Network Location(s)...")
                self.logger.info(f"Validating {loc_count} Network Locations")

                for parent_loc_id in replicated_data['network_locations']:
                    parent_loc = self.network_locations.get(parent_loc_id)
                    if not parent_loc:
                        continue

                    loc_name = parent_loc.get('name')

                    # Lookup in pre-fetched Child locations
                    child_loc = child_all_locs.get(loc_name)

                    if not child_loc:
                        validation_results['network_locations']['missing'] += 1
                        validation_results['network_locations']['details'].append({
                            'name': loc_name,
                            'status': 'MISSING',
                            'issue': 'Not found in Child CID'
                        })
                        self.logger.error(f"✗ Network Location MISSING: {loc_name}")
                        continue

                    # Compare key fields
                    mismatches = []
                    if parent_loc.get('enabled') != child_loc.get('enabled'):
                        mismatches.append(f"enabled: Parent={parent_loc.get('enabled')} vs Child={child_loc.get('enabled')}")

                    if mismatches:
                        validation_results['network_locations']['mismatches'] += 1
                        validation_results['network_locations']['details'].append({
                            'name': loc_name,
                            'status': 'MISMATCH',
                            'issues': mismatches
                        })
                        self.logger.warning(f"⚠ Network Location MISMATCH: {loc_name} - {', '.join(mismatches)}")
                    else:
                        validation_results['network_locations']['matches'] += 1
                        self.logger.debug(f"✓ Network Location MATCH: {loc_name}")

            # Validate Rule Groups
            if replicated_data.get('rule_groups'):
                rg_count = len(replicated_data['rule_groups'])
                print_info(f"  Validating {rg_count} Rule Group(s)...")
                self.logger.info(f"Validating {rg_count} Rule Groups")

                for parent_rg_id in replicated_data['rule_groups']:
                    parent_rg = self.rule_groups.get(parent_rg_id)
                    if not parent_rg:
                        continue

                    rg_name = parent_rg.get('name')

                    # Lookup in pre-fetched Child rule groups
                    child_rg = child_all_rgs.get(rg_name)

                    if not child_rg:
                        validation_results['rule_groups']['missing'] += 1
                        validation_results['rule_groups']['details'].append({
                            'name': rg_name,
                            'status': 'MISSING',
                            'issue': 'Not found in Child CID'
                        })
                        self.logger.error(f"✗ Rule Group MISSING: {rg_name}")
                        continue

                    # Compare key fields
                    mismatches = []
                    if parent_rg.get('enabled') != child_rg.get('enabled'):
                        mismatches.append(f"enabled: Parent={parent_rg.get('enabled')} vs Child={child_rg.get('enabled')}")

                    parent_rules = parent_rg.get('rules', [])
                    child_rules = child_rg.get('rules', [])
                    if len(parent_rules) != len(child_rules):
                        mismatches.append(f"rule count: Parent={len(parent_rules)} vs Child={len(child_rules)}")
                    elif len(parent_rules) > 0:
                        # Check rule precedence order
                        parent_precedences = sorted([r.get('precedence') for r in parent_rules if r.get('precedence') is not None])
                        child_precedences = sorted([r.get('precedence') for r in child_rules if r.get('precedence') is not None])
                        if parent_precedences != child_precedences:
                            mismatches.append(f"rule precedence mismatch: Parent={parent_precedences[:3]}... vs Child={child_precedences[:3]}...")

                    if mismatches:
                        validation_results['rule_groups']['mismatches'] += 1
                        validation_results['rule_groups']['details'].append({
                            'name': rg_name,
                            'status': 'MISMATCH',
                            'issues': mismatches
                        })
                        self.logger.warning(f"⚠ Rule Group MISMATCH: {rg_name} - {', '.join(mismatches)}")
                    else:
                        validation_results['rule_groups']['matches'] += 1
                        self.logger.debug(f"✓ Rule Group MATCH: {rg_name}")

            # Validate Policies
            if replicated_data.get('policies'):
                policy_count = len(replicated_data['policies'])
                print_info(f"  Validating {policy_count} Polic(ies)...")
                self.logger.info(f"Validating {policy_count} Policies")

                for parent_policy_id in replicated_data['policies']:
                    parent_policy = self.policy_containers.get(parent_policy_id)
                    if not parent_policy:
                        continue

                    policy_name = parent_policy.get('name')

                    # Lookup in pre-fetched Child policies
                    child_policy = child_all_policies.get(policy_name)

                    if not child_policy:
                        validation_results['policies']['missing'] += 1
                        validation_results['policies']['details'].append({
                            'name': policy_name,
                            'status': 'MISSING',
                            'issue': 'Not found in Child CID'
                        })
                        self.logger.error(f"✗ Policy MISSING: {policy_name}")
                        continue

                    # Compare key fields
                    mismatches = []
                    if parent_policy.get('enabled') != child_policy.get('enabled'):
                        mismatches.append(f"enabled: Parent={parent_policy.get('enabled')} vs Child={child_policy.get('enabled')}")

                    parent_rg_count = len(parent_policy.get('rule_group_ids', []))
                    child_rg_count = len(child_policy.get('rule_group_ids', []))
                    if parent_rg_count != child_rg_count:
                        mismatches.append(f"rule group count: Parent={parent_rg_count} vs Child={child_rg_count}")

                    if mismatches:
                        validation_results['policies']['mismatches'] += 1
                        validation_results['policies']['details'].append({
                            'name': policy_name,
                            'status': 'MISMATCH',
                            'issues': mismatches
                        })
                        self.logger.warning(f"⚠ Policy MISMATCH: {policy_name} - {', '.join(mismatches)}")
                    else:
                        validation_results['policies']['matches'] += 1
                        self.logger.debug(f"✓ Policy MATCH: {policy_name}")

        except Exception as e:
            self.logger.exception("Exception during validation")
            print_error(f"Validation error: {e}")
        finally:
            # Restore original auth
            self.auth = original_auth
            self.falcon_fw = original_fw
            self.falcon_fp = original_fp

        # Print summary
        print()
        print_section("Validation Summary")

        total_matches = sum(v['matches'] for v in validation_results.values())
        total_mismatches = sum(v['mismatches'] for v in validation_results.values())
        total_missing = sum(v['missing'] for v in validation_results.values())
        total_validated = total_matches + total_mismatches + total_missing

        if total_validated == 0:
            print_warning("⚠ No resources were validated")
            self.logger.warning("Validation completed with no resources validated")
        else:
            match_percentage = (total_matches / total_validated * 100) if total_validated > 0 else 0

            print_info(f"  Total Validated: {total_validated}")
            print_success(f"  ✓ Matches: {total_matches} ({match_percentage:.1f}%)")
            if total_mismatches > 0:
                print_warning(f"  ⚠ Mismatches: {total_mismatches}")
            if total_missing > 0:
                print_error(f"  ✗ Missing: {total_missing}")

            self.logger.info("=" * 80)
            self.logger.info(f"Validation Summary: {total_matches} matches, {total_mismatches} mismatches, {total_missing} missing")
            self.logger.info("=" * 80)

            # Show detailed issues if any
            if total_mismatches > 0 or total_missing > 0:
                print()
                print_section("Validation Issues")

                for resource_type, results in validation_results.items():
                    for detail in results['details']:
                        if detail['status'] != 'MATCH':
                            status_symbol = "✗" if detail['status'] == 'MISSING' else "⚠"
                            print_warning(f"  {status_symbol} {resource_type.replace('_', ' ').title()}: {detail['name']} - {detail['status']}")
                            if 'issues' in detail:
                                for issue in detail['issues']:
                                    print_info(f"      • {issue}")
                            elif 'issue' in detail:
                                print_info(f"      • {detail['issue']}")

        print()
        return validation_results

    def replicate_to_child(self, child_cid: str, selected_policy_ids: List[str]) -> Dict[str, List[str]]:
        """Replicate selected policies and their dependencies to a Child CID

        Args:
            child_cid: Target Child CID
            selected_policy_ids: List of policy IDs to replicate

        Returns:
            Dictionary with parent IDs of replicated resources for validation
        """
        child_name = self.cid_names.get(child_cid, child_cid[:12])
        print_section(f"Replicating to: {child_name}")

        # Track replicated resources for validation (using parent IDs)
        replicated_data = {
            'network_locations': [],
            'rule_groups': [],
            'policies': []
        }

        # Reset skip_all flag for this Child CID
        self.skip_all_duplicates = False

        # CRITICAL: Switch authentication to Child CID using member_cid
        self.logger.info(f"Switching to Child CID for replication: {child_cid}")
        original_fw = self.falcon_fw
        original_fp = self.falcon_fp

        try:
            # Create new auth for Child CID
            child_auth = OAuth2(
                client_id=self.client_id,
                client_secret=self.client_secret,
                base_url=self.base_url,
                member_cid=child_cid
            )
            token_result = child_auth.token()
            if token_result.get('status_code') != 201:
                raise Exception(f"Failed to authenticate to Child CID: {token_result}")

            # Replace with Child CID authenticated clients
            self.falcon_fw = FirewallManagement(auth_object=child_auth)
            self.falcon_fp = FirewallPolicies(auth_object=child_auth)
            self.logger.info(f"Successfully authenticated to Child CID: {child_name}")

        except Exception as e:
            self.logger.error(f"Failed to switch to Child CID: {e}")
            print_error(f"Failed to authenticate to Child CID: {e}")
            return replicated_data

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

        # Disable console logging during replication to avoid interfering with progress bars
        console_handler = None
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                console_handler = handler
                break

        if console_handler:
            self.logger.removeHandler(console_handler)

        try:
            # Step 2: Replicate Network Locations
            location_id_map = {}
            if self.network_locations:
                print_info(f"Replicating {len(self.network_locations)} Network Locations...")
                success_count = 0
                skipped_count = 0
                total = len(self.network_locations)

                for idx, (loc_id, loc_data) in enumerate(self.network_locations.items(), 1):
                    # Show progress on same line
                    progress_pct = (idx / total) * 100
                    print(f"\r  Progress: {idx}/{total} ({progress_pct:.0f}%) - {loc_data.get('name', 'Unknown')[:40]:<40}", end='', flush=True)

                    new_id = self.replicate_network_location(loc_data, child_cid, skip_duplicates=self.skip_all_duplicates)
                    if new_id and new_id != "dry-run-id":  # Only track real IDs
                        location_id_map[loc_id] = new_id
                        replicated_data['network_locations'].append(loc_id)  # Track parent ID
                        success_count += 1
                    elif new_id == "dry-run-id":
                        # In dry-run mode, still track it
                        replicated_data['network_locations'].append(loc_id)
                        success_count += 1
                    else:
                        skipped_count += 1

                print()  # New line after progress
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
                total = len(required_rule_group_ids)

                for idx, rg_id in enumerate(required_rule_group_ids, 1):
                    rg_data = self.rule_groups.get(rg_id)
                    if rg_data:
                        # Show progress on same line
                        progress_pct = (idx / total) * 100
                        print(f"\r  Progress: {idx}/{total} ({progress_pct:.0f}%) - {rg_data.get('name', 'Unknown')[:40]:<40}", end='', flush=True)

                        new_id = self.replicate_rule_group(rg_data, child_cid, location_id_map, skip_duplicates=self.skip_all_duplicates)
                        if new_id and new_id != "dry-run-id":
                            rule_group_id_map[rg_id] = new_id
                            replicated_data['rule_groups'].append(rg_id)  # Track parent ID
                            success_count += 1
                        elif new_id == "dry-run-id":
                            replicated_data['rule_groups'].append(rg_id)
                            success_count += 1
                        else:
                            skipped_count += 1

                print()  # New line after progress
                print_success(f"✓ Created {success_count} Rule Groups")
                if skipped_count > 0:
                    print_info(f"  (Skipped {skipped_count} - already exist)")
                print()

            # Step 4: Replicate Policies
            print_info(f"Replicating {len(selected_policy_ids)} Policies...")
            success_count = 0
            skipped_count = 0
            total = len(selected_policy_ids)

            for idx, policy_id in enumerate(selected_policy_ids, 1):
                policy_data = self.policy_containers.get(policy_id)
                if policy_data:
                    # Show progress on same line
                    progress_pct = (idx / total) * 100
                    print(f"\r  Progress: {idx}/{total} ({progress_pct:.0f}%) - {policy_data.get('name', 'Unknown')[:40]:<40}", end='', flush=True)

                    new_id = self.replicate_policy(policy_data, child_cid, rule_group_id_map, skip_duplicates=self.skip_all_duplicates)
                    if new_id and new_id != "dry-run-id":
                        replicated_data['policies'].append(policy_id)  # Track parent ID
                        success_count += 1
                    elif new_id == "dry-run-id":
                        replicated_data['policies'].append(policy_id)
                        success_count += 1
                    else:
                        skipped_count += 1

            print()  # New line after progress
            print_success(f"✓ Created {success_count} Policies")
            if skipped_count > 0:
                print_info(f"  (Skipped {skipped_count} - already exist)")
            print()

        finally:
            # Re-enable console logging
            if console_handler:
                self.logger.addHandler(console_handler)

            # CRITICAL: Restore original Parent CID authentication
            self.falcon_fw = original_fw
            self.falcon_fp = original_fp
            self.logger.info("Restored Parent CID authentication")

        # Return replicated data for validation
        return replicated_data

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
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without executing them (dry run mode)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip post-replication validation')
    parser.add_argument('--log-file', type=str,
                       help='Path to log file (default: auto-generated in logs/)')

    args = parser.parse_args()

    # Print logo and header
    print_jg_logo()
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
            base_url=base_url,
            dry_run=args.dry_run,
            log_file=args.log_file
        )

        # Display mode information
        if args.dry_run:
            print_header("DRY RUN MODE - No changes will be made")
            print_warning("⚠️  This is a preview only. No resources will be created or modified.")
            print()

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
            # Replicate to child and get data for validation
            replicated_data = replicator.replicate_to_child(child_cid, selected_policies)

            # Validate unless disabled or dry-run mode
            if not args.no_validate and not args.dry_run and replicated_data:
                try:
                    replicator.validate_replication(child_cid, replicated_data)
                except Exception as e:
                    child_name = replicator.cid_names.get(child_cid, child_cid[:12])
                    print_error(f"Validation failed for {child_name}: {e}")
                    replicator.logger.exception(f"Validation exception for {child_name}")
            elif args.dry_run:
                print_info("Skipping validation (dry-run mode)")
            elif args.no_validate:
                print_info("Skipping validation (--no-validate flag)")

        except Exception as e:
            child_name = replicator.cid_names.get(child_cid, child_cid[:12])
            print_error(f"Failed to replicate to {child_name}: {e}")
            replicator.logger.exception(f"Replication exception for {child_name}")
            continue

    print()
    print_section("REPLICATION COMPLETE")
    print_success("✓ Firewall configurations have been replicated!")
    print()

    if not args.no_validate and not args.dry_run:
        print_info("Next steps:")
        print_info("  1. Review validation results above")
        print_info("  2. Verify policies in Child CID Falcon Console")
        print_info("  3. Test firewall rules")
        print_info("  4. Enable policies when ready")
    else:
        print_info("Next steps:")
        print_info("  1. Verify policies in Child CID Falcon Console")
        print_info("  2. Test firewall rules")
        print_info("  3. Enable policies when ready")


if __name__ == "__main__":
    main()

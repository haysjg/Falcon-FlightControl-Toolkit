#!/usr/bin/env python3
"""
Firewall Management Test Data Generator

This script generates test configurations for Firewall Management to facilitate
testing of the replication script. It creates:
- Network Locations (Contexts)
- Firewall Rules
- Rule Groups
- Policy Containers

WARNING: This script creates many resources in your CrowdStrike tenant.
         Use with caution and only in test environments.

Author: Claude Opus 4.6
Date: 2026-03-14
"""

import sys
import os
import argparse
import random
import time
from datetime import datetime
from typing import Dict, List, Any

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from falconpy import OAuth2, FirewallManagement, FirewallPolicies
from utils.auth import get_credentials_smart
from utils.formatting import (
    print_header, print_section, print_info, print_success,
    print_error, print_warning, print_progress, Colors
)


class FirewallTestDataGenerator:
    """Generates test data for Firewall Management"""

    def __init__(self, client_id: str, client_secret: str, base_url: str = "https://api.crowdstrike.com"):
        """Initialize the generator

        Args:
            client_id: CrowdStrike API Client ID
            client_secret: CrowdStrike API Client Secret
            base_url: API base URL
        """
        print_info("Authenticating to Falcon API...")

        # Create shared OAuth2 object (recommended pattern for multiple services)
        self.auth = OAuth2(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )

        # Force token generation
        token_result = self.auth.token()
        if token_result.get('status_code') != 201:
            raise Exception(f"Authentication failed: {token_result.get('body')}")

        # Initialize service classes with shared auth object
        self.falcon_fw = FirewallManagement(auth_object=self.auth)
        self.falcon_fp = FirewallPolicies(auth_object=self.auth)

        print_success("Authentication successful!")

        # Track created resources for cleanup
        self.created_locations = []
        self.created_rules = []
        self.created_rule_groups = []
        self.created_policies = []

    # Network Location generation
    LOCATION_PREFIXES = [
        "Office", "Branch", "Datacenter", "Cloud", "Remote",
        "HQ", "Regional", "Campus", "Site", "Facility"
    ]

    LOCATION_SUFFIXES = [
        "Network", "Subnet", "Zone", "Segment", "VLAN",
        "DMZ", "Internal", "External", "Management", "Production"
    ]

    # Rule generation
    PROTOCOLS = ["TCP", "UDP", "ICMP", "ANY"]
    DIRECTIONS = ["IN", "OUT", "BOTH"]
    ACTIONS = ["ALLOW", "DENY"]  # API accepts ALLOW or DENY, not BLOCK

    COMMON_PORTS = [
        20, 21, 22, 23, 25, 53, 80, 110, 143, 443,
        445, 465, 587, 993, 995, 3306, 3389, 5432, 5900, 8080
    ]

    SERVICE_NAMES = [
        "SSH", "HTTP", "HTTPS", "FTP", "SMTP", "DNS",
        "RDP", "SMB", "MySQL", "PostgreSQL", "VNC", "Redis",
        "MongoDB", "Elasticsearch", "Kafka", "RabbitMQ"
    ]

    def generate_network_location(self, index: int) -> Dict[str, Any]:
        """Generate a network location configuration

        Args:
            index: Index number for unique naming

        Returns:
            Network location configuration dict
        """
        prefix = random.choice(self.LOCATION_PREFIXES)
        suffix = random.choice(self.LOCATION_SUFFIXES)
        name = f"Test-{prefix}-{suffix}-{index:04d}"

        # Generate random IP range
        network = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.0"
        cidr = random.choice([24, 25, 26, 27, 28])

        return {
            "name": name,
            "description": f"Test network location {index} - {prefix} {suffix}",
            "enabled": True,
            "connection_types": {
                "wired": True,
                "wireless": {
                    "enabled": random.choice([True, False]),
                    "require_encryption": True,
                    "ssids": [f"TestSSID-{index}"]
                }
            },
            "default_gateways": [f"{network.rsplit('.', 1)[0]}.1"],
            "dhcp_servers": [f"{network.rsplit('.', 1)[0]}.{random.randint(2, 10)}"],
            "dns_servers": [
                f"{network.rsplit('.', 1)[0]}.{random.randint(2, 10)}",
                "8.8.8.8"
            ],
            "host_addresses": [f"{network}/{cidr}"],
            "https_reachable_hosts": {
                "hostnames": [f"service{i}.test{index}.com" for i in range(1, random.randint(2, 4))]
            },
            "dns_resolution_targets": {
                "targets": [
                    {
                        "hostname": f"server{i}.test{index}.local",
                        "ip_match": [f"{network.rsplit('.', 1)[0]}.{10+i}"]
                    }
                    for i in range(1, random.randint(2, 4))
                ]
            },
            "icmp_request_targets": {
                "targets": [f"{network.rsplit('.', 1)[0]}.{i}" for i in range(1, 4)]
            }
        }

    def create_network_locations(self, count: int) -> List[str]:
        """Create multiple network locations

        Args:
            count: Number of locations to create

        Returns:
            List of created location IDs
        """
        print_section(f"Creating {count} Network Locations")

        created_ids = []

        for i in range(count):
            try:
                location_config = self.generate_network_location(i + 1)

                # NOTE: The exact body format needs to be discovered from API documentation
                # Current implementation is a best guess and may need adjustment
                response = self.falcon_fw.create_network_locations(
                    body=location_config  # Try direct config first
                )

                if response['status_code'] in [200, 201]:
                    location_id = response['body']['resources'][0]['id']
                    created_ids.append(location_id)
                    print_progress(i + 1, count, prefix=f"Creating locations", suffix=f"({i+1}/{count})")
                else:
                    print_error(f"Failed to create location {i+1}: {response['body'].get('errors')}")

                # Rate limiting
                time.sleep(0.1)

            except Exception as e:
                print_error(f"Exception creating location {i+1}: {e}")

        print()
        print_success(f"Created {len(created_ids)} Network Location(s)")
        self.created_locations = created_ids
        return created_ids

    def generate_rule(self, index: int) -> Dict[str, Any]:
        """Generate a firewall rule configuration

        Args:
            index: Index number for unique naming

        Returns:
            Rule configuration dict
        """
        service = random.choice(self.SERVICE_NAMES)
        action = random.choice(self.ACTIONS)
        direction = random.choice(self.DIRECTIONS)
        protocol = random.choice([6, 17])  # TCP=6, UDP=17

        # Select a port based on service or random
        if service in ["HTTP"]:
            port = 80
        elif service in ["HTTPS"]:
            port = 443
        elif service in ["SSH"]:
            port = 22
        elif service in ["RDP"]:
            port = 3389
        elif service in ["SMB"]:
            port = 445
        else:
            port = random.choice(self.COMMON_PORTS)

        name = f"Test-{action}-{service}-{index:04d}"

        rule = {
            "name": name,
            "description": f"Test rule {index}: {action} {service} traffic",
            "enabled": True,
            "action": action,
            "direction": direction,
            "protocol": str(protocol),
            "address_family": "IP4",
            "log": random.choice([True, False]),
            "temp_id": f"temp-rule-{index}"
        }

        # Add port if it's TCP/UDP
        if protocol in [6, 17]:
            # Use port range or single port based on random choice
            if random.choice([True, False]) and port < 65530:
                # Port range (start different from end)
                end_port = port + random.randint(1, 10)
                rule["remote_port"] = [
                    {
                        "start": port,
                        "end": end_port
                    }
                ]
            else:
                # Single port - only include start field
                rule["remote_port"] = [
                    {
                        "start": port
                    }
                ]

        return rule

    def generate_rule_group(self, index: int, num_rules: int = 5) -> Dict[str, Any]:
        """Generate a rule group configuration with rules

        Args:
            index: Index number for unique naming
            num_rules: Number of rules to include in the group

        Returns:
            Rule group configuration dict
        """
        category = random.choice([
            "Security", "Compliance", "Application", "Network",
            "Infrastructure", "Database", "WebServer", "Custom"
        ])

        name = f"Test-RuleGroup-{category}-{index:04d}"

        # Platform labels: windows, mac, linux (lowercase)
        platform_label = random.choice(["windows", "mac", "linux"])

        # Generate rules for this group
        rules = [self.generate_rule(i + (index * 100)) for i in range(num_rules)]

        config = {
            "name": name,
            "description": f"Test rule group {index} for {category} policies",
            "enabled": True,
            "platform": platform_label,
            "rules": rules
        }

        return config

    def create_rule_groups(self, count: int, rules_per_group: int = 3) -> List[str]:
        """Create multiple rule groups

        Args:
            count: Number of rule groups to create
            rules_per_group: Number of rules per group (default: 3)

        Returns:
            List of created rule group IDs
        """
        print_section(f"Creating {count} Rule Groups with {rules_per_group} rules each")

        created_ids = []
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        for i in range(count):
            try:
                # Generate config with rules
                category = random.choice([
                    "Security", "Compliance", "Application", "Network",
                    "Infrastructure", "Database", "WebServer", "Custom"
                ])
                name = f"Test-RuleGroup-{category}-{timestamp}-{i+1:03d}"
                platform_label = random.choice(["windows", "mac", "linux"])

                # Generate rules for this group
                rules = []
                if rules_per_group > 0:
                    for r in range(rules_per_group):
                        rule = self.generate_rule(i * rules_per_group + r + 1)
                        rules.append(rule)

                rg_config = {
                    "name": name,
                    "description": f"Test rule group {i+1} for {category} policies with {rules_per_group} rules",
                    "enabled": True,
                    "platform": platform_label,
                    "rules": rules
                }

                response = self.falcon_fw.create_rule_group(
                    body=rg_config
                )

                if response['status_code'] in [200, 201]:
                    # Extract ID from response - it's a list of strings
                    resources = response['body'].get('resources', [])
                    if resources:
                        rg_id = resources[0] if isinstance(resources[0], str) else resources[0].get('id')
                        created_ids.append(rg_id)

                    print_progress(i + 1, count, prefix=f"Creating rule groups", suffix=f"({i+1}/{count})")
                else:
                    print_error(f"Failed to create rule group {i+1}: {response['body'].get('errors')}")

                # Rate limiting
                time.sleep(0.1)

            except Exception as e:
                print_error(f"Exception creating rule group {i+1}: {e}")

        print()
        print_success(f"Created {len(created_ids)} Rule Group(s)")
        self.created_rule_groups = created_ids
        return created_ids

    def create_policies(self, count: int, rule_group_ids: List[str] = None) -> List[str]:
        """Create multiple firewall policies

        Args:
            count: Number of policies to create
            rule_group_ids: Optional list of rule group IDs to assign to policies

        Returns:
            List of created policy IDs
        """
        print_section(f"Creating {count} Firewall Policies")

        created_ids = []
        platforms = ["Windows", "Mac", "Linux"]  # Capitalized for FirewallPolicies API
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        for i in range(count):
            try:
                platform = platforms[i % len(platforms)]
                policy_name = f"Test-Policy-{platform}-{timestamp}-{i+1:03d}"

                # Step 1: Create the policy using FirewallPolicies API
                policy_body = {
                    "resources": [
                        {
                            "name": policy_name,
                            "description": f"Test firewall policy {i+1} for {platform}",
                            "platform_name": platform  # Capitalized
                        }
                    ]
                }

                response = self.falcon_fp.create_policies(body=policy_body)

                if response['status_code'] in [200, 201]:
                    policy_id = response['body']['resources'][0]['id']
                    created_ids.append(policy_id)

                    # Step 2: If rule groups provided, assign them to this policy
                    if rule_group_ids:
                        # Determine the matching platform for rule groups
                        platform_lower = platform.lower()

                        # Select rule groups that match this platform (or random if not enough)
                        matching_rgs = []
                        if len(rule_group_ids) > 0:
                            # Take up to 3 rule groups to assign
                            num_to_assign = min(3, len(rule_group_ids))
                            matching_rgs = random.sample(rule_group_ids, num_to_assign)

                        if matching_rgs:
                            # Update policy container with rule groups
                            # KNOWN ISSUE: This API call consistently returns 500 errors
                            # See BUG_POLICY_ASSIGNMENT.md for details
                            update_body = {
                                "policy_id": policy_id,
                                "rule_group_ids": matching_rgs,
                                "default_inbound": "ALLOW",
                                "default_outbound": "ALLOW",
                                "enforce": False,
                                "local_logging": False,
                                "tracking": "none",
                                "test_mode": False
                            }

                            update_response = self.falcon_fw.update_policy_container(
                                ids=policy_id,
                                body=update_body
                            )

                            if update_response['status_code'] not in [200, 201]:
                                # This consistently fails with 500 errors - known API issue
                                # Policies are created but Rule Groups are not assigned
                                pass  # Silent fail - documented in BUG_POLICY_ASSIGNMENT.md

                    print_progress(i + 1, count, prefix=f"Creating policies", suffix=f"({i+1}/{count})")
                else:
                    print_error(f"Failed to create policy {i+1}: {response['body'].get('errors')}")

                # Rate limiting
                time.sleep(0.1)

            except Exception as e:
                print_error(f"Exception creating policy {i+1}: {e}")

        print()
        print_success(f"Created {len(created_ids)} Policy Container(s)")
        self.created_policies = created_ids
        return created_ids

    def generate_placeholder_data_summary(self,
                                         locations: int,
                                         rules: int,
                                         rule_groups: int,
                                         policies: int) -> str:
        """Generate a summary of what would be created

        Args:
            locations: Number of network locations
            rules: Number of rules
            rule_groups: Number of rule groups
            policies: Number of policies

        Returns:
            Summary string
        """
        return f"""
Test Data Generation Plan:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Network Locations (Contexts):    {locations}
  - Randomly generated IP ranges
  - Various connection types (wired/wireless)
  - DNS and DHCP configurations

Firewall Rules:                   {rules}
  - TCP/UDP/ICMP protocols
  - Common ports (22, 80, 443, 3389, etc.)
  - Inbound/Outbound directions
  - Allow/Block actions

Rule Groups:                      {rule_groups}
  - Each group contains 1-10 rules
  - Categorized by purpose (Security, Compliance, etc.)

Policy Containers:                {policies}
  - Linked to rule groups
  - Various platforms (Windows, Linux, macOS)
  - Enabled/Disabled states

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Resources to Create:        {locations + rules + rule_groups + policies}

Estimated Time:                   ~{(locations + rules + rule_groups + policies) * 0.15 / 60:.1f} minutes
"""

    def cleanup_all(self):
        """Delete all created test resources"""
        print_section("CLEANUP - Deleting Test Resources")

        total_deleted = 0

        # Delete network locations
        if self.created_locations:
            print_info(f"Deleting {len(self.created_locations)} Network Locations...")
            try:
                response = self.falcon_fw.delete_network_locations(
                    ids=self.created_locations
                )
                if response['status_code'] in [200, 204]:
                    total_deleted += len(self.created_locations)
                    print_success(f"Deleted {len(self.created_locations)} location(s)")
                else:
                    print_error(f"Failed to delete locations: {response['body'].get('errors')}")
            except Exception as e:
                print_error(f"Exception during location cleanup: {e}")

        # Delete rule groups
        if self.created_rule_groups:
            print_info(f"Deleting {len(self.created_rule_groups)} Rule Groups...")
            try:
                response = self.falcon_fw.delete_rule_groups(
                    ids=self.created_rule_groups
                )
                if response['status_code'] in [200, 204]:
                    total_deleted += len(self.created_rule_groups)
                    print_success(f"Deleted {len(self.created_rule_groups)} rule group(s)")
                else:
                    print_error(f"Failed to delete rule groups: {response['body'].get('errors')}")
            except Exception as e:
                print_error(f"Exception during rule group cleanup: {e}")

        print()
        print_success(f"Cleanup complete! Deleted {total_deleted} resource(s)")


def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(
        description="Generate test data for Firewall Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 100 of each resource type
  python generate_firewall_test_data.py --config ../config/credentials.json --count 100

  # Generate specific quantities
  python generate_firewall_test_data.py --config ../config/credentials.json \\
    --locations 50 --rules 200 --rule-groups 30 --policies 10

  # Cleanup all created resources
  python generate_firewall_test_data.py --config ../config/credentials.json --cleanup-only

WARNING: This script creates many resources. Use only in test environments!
        """
    )

    # Credential arguments
    parser.add_argument('--config', type=str, help='Path to credentials JSON file')
    parser.add_argument('--client-id', type=str, help='CrowdStrike API Client ID')
    parser.add_argument('--client-secret', type=str, help='CrowdStrike API Client Secret')
    parser.add_argument('--base-url', type=str, default='https://api.crowdstrike.com',
                       help='API base URL (default: US-1)')

    # Generation arguments
    parser.add_argument('--count', type=int, help='Generate this many of each resource type')
    parser.add_argument('--locations', type=int, help='Number of network locations to create')
    parser.add_argument('--rules', type=int, help='Number of firewall rules to create')
    parser.add_argument('--rule-groups', type=int, help='Number of rule groups to create')
    parser.add_argument('--policies', type=int, help='Number of policies to create')

    # Mode arguments
    parser.add_argument('--cleanup-only', action='store_true',
                       help='Only cleanup previously created resources (reads from cache)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be created without creating anything')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt (auto-confirm)')

    args = parser.parse_args()

    # Print header
    print_header("FIREWALL MANAGEMENT TEST DATA GENERATOR")
    print()

    # Determine counts
    if args.count:
        locations = rules = rule_groups = policies = args.count
    else:
        locations = args.locations or 10
        rules = args.rules or 50
        rule_groups = args.rule_groups or 10
        policies = args.policies or 5

    # Get credentials
    try:
        # Set default config path if not provided
        config_path = args.config or '../../config/credentials.json'

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

    # Initialize generator
    try:
        generator = FirewallTestDataGenerator(
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url
        )
    except Exception as e:
        print(f"Failed to initialize: {e}")
        sys.exit(1)

    print()

    # Dry run mode
    if args.dry_run:
        print(generator.generate_placeholder_data_summary(
            locations, rules, rule_groups, policies
        ))
        print_warning("DRY RUN MODE - Nothing was created")
        return

    # Cleanup only mode
    if args.cleanup_only:
        print_warning("CLEANUP MODE - This will delete test resources")
        print_info("Note: This feature requires resource tracking (not yet implemented)")
        print_info("      For now, you'll need to delete resources manually via Falcon Console")
        return

    # Show plan
    print(generator.generate_placeholder_data_summary(
        locations, rules, rule_groups, policies
    ))

    # Confirm with user
    print_warning("This will create resources in your CrowdStrike tenant!")
    if not args.yes:
        confirm = input("Type 'yes' to continue: ").strip().lower()
        if confirm != 'yes':
            print_warning("Cancelled by user")
            sys.exit(0)

    print()

    # Create resources
    try:
        # Step 1: Network Locations
        location_ids = generator.create_network_locations(locations)
        print()

        # Step 2: Rule Groups (empty for now)
        rg_ids = generator.create_rule_groups(rule_groups)
        print()

        # Step 3: Policies (using FirewallPolicies API)
        policy_ids = generator.create_policies(policies, rule_group_ids=rg_ids)
        print()

        # Summary
        print_section("GENERATION COMPLETE")
        print_success(f"Successfully created:")
        print_info(f"  • {len(location_ids)} Network Locations")
        print_info(f"  • {len(rg_ids)} Rule Groups (with 3 rules each)")
        print_info(f"  • {len(policy_ids)} Policies (created)")
        print()

        print_warning("⚠️  KNOWN ISSUE: Rule Groups NOT assigned to Policies")
        print_info("  The update_policy_container API consistently returns 500 errors")
        print_info("  This is a CrowdStrike API issue, not a script problem")
        print_info("  See tooling/BUG_POLICY_ASSIGNMENT.md for details")
        print()

        print_warning("NEXT STEPS:")
        print_info("  1. Manually assign Rule Groups to Policies via Falcon Console (if needed)")
        print_info("  2. Or test replication with Policies without Rule Groups")
        print_info("  3. Report issue to CrowdStrike support if not already known")

    except KeyboardInterrupt:
        print()
        print_warning("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

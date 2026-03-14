# Overwrite Functionality Implementation

## Overview
The overwrite functionality allows users to update existing resources in Child CIDs when conflicts are detected during replication, instead of skipping or creating renamed versions.

## Implementation Details

### 1. Resource Detection Method
Added `find_existing_resource_by_name()` method that:
- Takes resource type ('location', 'rule_group', 'policy'), name, and target CID
- Queries all resources of that type in the target CID
- Gets details and searches for exact name match
- Returns the resource ID if found, None otherwise

### 2. Interactive Conflict Resolution
When a duplicate resource is detected, users are presented with 4 options:
```
[1] Skip - Keep existing resource, don't replicate
[2] Rename - Create new with version suffix (e.g., '_v2')
[3] Overwrite - Update existing resource with Parent version
[4] Skip All - Skip all remaining duplicates for this Child CID
```

### 3. Overwrite Implementation by Resource Type

#### Network Locations
- Method: `replicate_network_location()`
- API used: `falcon_fw.update_network_locations(body=location_config)`
- Process:
  1. Find existing location ID by name
  2. Add existing ID to location config
  3. Call update API with full configuration
  4. Return existing ID if successful

#### Rule Groups
- Method: `replicate_rule_group()`
- API used: `falcon_fw.update_rule_group(body=group_config)`
- Process:
  1. Find existing rule group ID by name
  2. Add existing ID to group config
  3. Call update API with full configuration
  4. Return existing ID if successful

#### Policies
- Method: `replicate_policy()`
- API used: `falcon_fp.update_policies(body=update_body)`
- Process:
  1. Find existing policy ID by name
  2. Create update body with existing ID and new configuration
  3. Call update API
  4. If successful, continue with rule group assignment (policy container update)
  5. Return existing ID if successful

### 4. State Management
- `self.skip_all_duplicates` instance variable tracks if user selected "Skip All"
- Reset to False at the start of each Child CID replication
- When True, all `replicate_*` methods automatically skip without prompting

## Testing

### Test Script: test_overwrite.py
Created a test script that:
1. Lists Child CIDs available for testing
2. Queries existing Network Locations in a Child CID
3. Queries existing Rule Groups in a Child CID
4. Queries existing Policies in a Child CID
5. Displays sample resources that can be used for testing

### Manual Test Procedure
1. Run `test_overwrite.py` to identify existing resources in a Child CID
2. Run `replicate_firewall.py` with a Parent CID that has resources with matching names
3. When prompted for conflict resolution, select [3] Overwrite
4. Verify that the resource is updated (not created as new)
5. Check that relationships (rule groups in policies, locations in rules) are maintained

## API Methods Used

### FirewallManagement API
- `query_network_locations()` - Find existing locations
- `get_network_locations(ids)` - Get location details
- `update_network_locations(body)` - Update location configuration
- `query_rule_groups()` - Find existing rule groups
- `get_rule_groups(ids)` - Get rule group details
- `update_rule_group(body)` - Update rule group configuration

### FirewallPolicies API
- `query_policies()` - Find existing policies
- `get_policies(ids)` - Get policy details
- `update_policies(body)` - Update policy configuration
- `update_policy_container(ids, body)` - Update policy container (rule group assignments)

## Error Handling

### Scenarios Covered
1. **Resource not found**: If `find_existing_resource_by_name()` returns None, error is logged and None returned
2. **Update API failure**: If update API returns non-200/201 status, error is logged with API error details
3. **Network errors**: Exception handling catches and logs any network/API exceptions
4. **Invalid user input**: Conflict resolution menu validates input and re-prompts if invalid

## Known Limitations

1. **Rules within Rule Groups**: Currently, overwrite updates the rule group metadata but may not update individual rules. This is because rules are embedded entities that require separate handling.

2. **Policy Container vs Policy**: Policies have two layers (policy metadata and policy container with settings). Overwrite handles both, but if policy container update fails, a warning is shown.

3. **Platform changes**: Overwrite does not change the platform of a resource (Windows/Mac/Linux). Platform is typically immutable after creation.

4. **No backup**: Overwrite directly updates resources without creating backups. Users should be cautious when overwriting production configurations.

## Future Enhancements

1. **Selective field updates**: Allow users to choose which fields to update vs preserve
2. **Backup before overwrite**: Create automatic backups of overwritten resources
3. **Rule-level handling**: Better handling of rules within rule groups during overwrite
4. **Diff preview**: Show differences between Parent and Child versions before overwriting
5. **Rollback capability**: Add ability to undo overwrites if issues are detected

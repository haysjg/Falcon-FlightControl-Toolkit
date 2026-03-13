# Custom IOAs Replicator

Replicate Custom IOA (Indicator of Attack) rule groups from Parent CID to Child CIDs in a CrowdStrike Falcon Flight Control environment.

## Overview

This script automates the replication of Custom IOA detection rules across your Flight Control hierarchy, optionally applying them to all prevention policies in the target Child CIDs.

## Features

- ✨ **Interactive IOA selection** - Choose which Custom IOAs to replicate
- ✨ **Interactive CID selection** - Choose target Child CIDs
- ✨ **Policy application** - Optionally apply IOAs to all prevention policies
- ✨ **Colored output** - Easy-to-read visual feedback
- ✨ **Progress indicators** - Real-time replication progress
- ✨ **Spinner animations** - Visual feedback during API calls
- ✨ **Multiple credential methods** - Config file, CLI args, or environment variables

## Prerequisites

- Python 3.9 or higher
- FalconPy SDK 1.6.0 or higher
- CrowdStrike Falcon API credentials with the following scopes:
  - **Custom IOA Rules: Read, Write**
  - **Prevention Policies: Read, Write** (if applying to policies)
  - **Flight Control: Read**
- Flight Control environment (Parent CID with Child CIDs)

## What are Custom IOAs?

Custom IOAs (Indicators of Attack) are custom detection rules you create to identify specific attack behaviors in your environment. They consist of:

- **Rule Groups**: Collections of related detection rules
- **Rules**: Individual detection logic (process execution, file operations, network activity, etc.)
- **Patterns**: Specific behaviors to detect
- **Severity**: Critical, High, Medium, Low, Informational
- **Disposition**: Actions to take (detect, prevent, monitor)

Unlike IOCs (Indicators of Compromise) which are static artifacts (hashes, IPs, domains), IOAs detect behavioral patterns that indicate an attack.

## Usage

### Interactive Mode (Default)

You'll be prompted to select IOAs and Child CIDs:

```bash
python replicate_custom_ioas.py --config ../config/credentials.json
```

**Selection Process:**
1. Script displays all Custom IOA rule groups from Parent CID
2. Select IOAs by numbers (e.g., `1,3,5`), `all`, or `q` to quit
3. Script displays all Child CIDs
4. Select children by numbers, `all`, or `q` to quit
5. Choose whether to apply IOAs to all prevention policies
6. Replication begins with visual progress indicators

### Non-Interactive Mode

Replicate all IOAs to all children without prompting:

```bash
python replicate_custom_ioas.py --config ../config/credentials.json --non-interactive
```

**Note:** Non-interactive mode does NOT apply IOAs to policies automatically (safety feature).

### Credential Methods

**Method 1: Config File (Recommended for testing)**
```bash
python replicate_custom_ioas.py --config ../config/credentials.json
```

**Method 2: Environment Variables (Recommended for production)**
```powershell
# PowerShell
$env:FALCON_CLIENT_ID = "your_client_id"
$env:FALCON_CLIENT_SECRET = "your_client_secret"
python replicate_custom_ioas.py
```

**Method 3: CLI Arguments**
```bash
python replicate_custom_ioas.py --client-id "YOUR_ID" --client-secret "YOUR_SECRET"
```

See [../CREDENTIALS_GUIDE.md](../CREDENTIALS_GUIDE.md) for detailed credential setup instructions.

## Visual Output

The script provides rich visual feedback:

```
════════════════════════════════════════════════════════════════════════════════
              FLIGHT CONTROL - CUSTOM IOAs REPLICATOR
════════════════════════════════════════════════════════════════════════════════

ℹ️ Authenticating to Falcon API...
✓ Authentication successful!

▶ Target: Production Servers
    ⠋ Replicating "Suspicious PowerShell Execution"...
    ✓ Replicated: Suspicious PowerShell Execution
      Applied to 3 prevention policy/policies
    ✓ Replicated: Credential Dumping Detection
      Applied to 3 prevention policy/policies

Overall progress [██████████████████████████████] 100% (Production Servers)

╔══════════════════════════════════════════════════════════════════════════════╗
║                         REPLICATION COMPLETE                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Custom IOAs replicated:      2                                              ║
║ Child CIDs targeted:          1                                              ║
║ Total operations:             2                                              ║
║ Successful:                   2                                              ║
║ Failed:                       0                                              ║
║ Applied to policies:          Yes                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## How It Works

### 1. Retrieval Phase
- Connects to Parent CID using Flight Control API
- Queries all Custom IOA rule groups
- Retrieves full rule group details including all rules

### 2. Selection Phase (Interactive)
- Displays all available Custom IOAs with:
  - Name and description
  - Enabled/Disabled status
  - Number of rules
  - Rule group ID
- User selects which IOAs to replicate
- User selects which Child CIDs to target

### 3. Policy Question
- Asks if IOAs should be applied to all prevention policies
- If yes: Each replicated IOA will be linked to all prevention policies in the Child CID
- If no: IOAs are created but not applied (can be applied manually later)

### 4. Replication Phase
For each selected Child CID:
- Creates the IOA rule group
- Creates each individual rule within the group
- Applies field values and patterns
- Optionally links to all prevention policies
- Shows real-time progress with spinner animation

### 5. Results
- Summary of successful and failed replications
- Count of policies updated (if applicable)

## Understanding IOA Structure

A Custom IOA consists of:

```
Rule Group (e.g., "Lateral Movement Detection")
├── Rule 1 (e.g., "PSExec Usage")
│   ├── Pattern: Process execution matching psexec*
│   ├── Severity: High
│   └── Disposition: Detect
├── Rule 2 (e.g., "Remote Service Creation")
│   ├── Pattern: Service creation on remote host
│   ├── Severity: High
│   └── Disposition: Prevent
└── Rule 3 (e.g., "WMI Remote Execution")
    ├── Pattern: WMI command execution
    ├── Severity: Medium
    └── Disposition: Detect
```

The script replicates the **entire structure** to Child CIDs.

## Applying to Prevention Policies

When you choose to apply IOAs to prevention policies:

1. The script queries all prevention policies in the Child CID
2. For each policy, it adds the replicated IOA rule group
3. The IOA becomes active for all hosts using that policy
4. Detections will be generated when the IOA patterns match

**Important:**
- IOAs are **additive** - they won't remove existing IOAs from policies
- Hosts must be assigned to the policies for IOAs to take effect
- IOAs can be disabled without removing them from policies

## Troubleshooting

### Authentication Errors

**Error:** `Authentication failed: 401`
- Verify your Client ID and Client Secret are correct
- Check that credentials have **Custom IOA Rules: Read, Write** scope
- Ensure base URL matches your Falcon cloud

### No Custom IOAs Found

**Message:** `No Custom IOAs found to replicate`
- Verify you have Custom IOAs created in the Parent CID
- Check you're authenticated to the correct Parent CID
- Ensure API credentials have **Custom IOA Rules: Read** scope

### Replication Fails

**Error:** `Failed: [IOA Name]`

Possible causes:
- **IOA already exists** in Child CID with same name
- **Insufficient permissions** in target Child CID
- **Invalid rule patterns** or configurations
- **API rate limiting** (script handles automatically)

**Solution:**
- Check if IOA already exists in Child CID (delete or rename it)
- Verify API credentials have Write permissions
- Review IOA configuration in Parent CID

### Cannot Apply to Policies

**Issue:** IOA replicated but not applied to policies

Possible causes:
- **No prevention policies** exist in Child CID
- **Insufficient permissions** for Prevention Policies
- **API errors** during policy update

**Solution:**
- Verify prevention policies exist: `python ../script_export_devices_policies/export_devices_policies.py`
- Check API credentials have **Prevention Policies: Write** scope
- Apply IOAs manually via Falcon console

## API Scopes Required

| Scope | Permission | Required For |
|-------|------------|--------------|
| Custom IOA Rules | Read | Reading IOAs from Parent CID |
| Custom IOA Rules | Write | Creating IOAs in Child CIDs |
| Prevention Policies | Read | Querying policies (if applying) |
| Prevention Policies | Write | Updating policies (if applying) |
| Flight Control | Read | Querying Child CIDs |

## Performance Considerations

- **Small environments:** <10 IOAs, <5 Children = ~30 seconds
- **Medium environments:** 10-50 IOAs, 5-20 Children = ~2-5 minutes
- **Large environments:** >50 IOAs, >20 Children = ~5-15 minutes

Performance factors:
- Number of IOAs selected
- Number of rules per IOA
- Number of Child CIDs
- Whether applying to policies (adds time)
- API rate limits (handled automatically)

## Best Practices

### 1. Test First
Always test with a single Child CID before replicating to all:
```bash
# Select just IOA #1 and Child #1 for testing
```

### 2. Review IOAs Before Replication
- Ensure IOAs are working correctly in Parent CID
- Verify severity and disposition are appropriate
- Test IOAs don't cause false positives

### 3. Staged Rollout
For large environments:
1. Replicate to test Child CID
2. Verify detections work correctly
3. Replicate to production Children in batches

### 4. Policy Application
Consider **NOT** applying to all policies immediately:
- Replicate IOAs first
- Test manually on specific policies
- Apply to all policies once validated

### 5. Documentation
Keep track of:
- Which IOAs were replicated when
- Which Child CIDs received which IOAs
- Any customizations per Child CID

## Differences from Manual Creation

| Aspect | Manual | Script |
|--------|--------|--------|
| Speed | Slow (minutes per CID) | Fast (seconds per CID) |
| Accuracy | Error-prone | Exact copy |
| Consistency | Varies | Identical |
| Policy Application | Manual | Automated |
| Documentation | None | Logged output |

## Limitations

### What the Script Does
- ✅ Replicates IOA rule groups
- ✅ Copies all rules and patterns
- ✅ Applies to prevention policies (optional)
- ✅ Handles API errors gracefully

### What the Script Doesn't Do
- ❌ Modify existing IOAs (only creates new ones)
- ❌ Delete IOAs from Child CIDs
- ❌ Sync changes (one-time replication)
- ❌ Validate IOA logic or patterns
- ❌ Test IOAs for false positives

### Important Notes
- **One-way replication:** Changes in Parent CID after replication are NOT automatically synced
- **Name conflicts:** If an IOA with the same name exists, replication fails
- **Manual updates:** If you modify an IOA in Parent CID, you must replicate again (or manually update Children)

## Example Workflows

### Workflow 1: New IOA Deployment
```bash
# Step 1: Create and test IOA in Parent CID (via console)
# Step 2: Replicate to test Child
python replicate_custom_ioas.py --config ../config/credentials.json
# Select: IOA #1, Child #1, No to policies

# Step 3: Test in Child CID for a few days
# Step 4: If good, replicate to all
python replicate_custom_ioas.py --config ../config/credentials.json
# Select: IOA #1, all children, Yes to policies
```

### Workflow 2: Bulk Migration
```bash
# Replicate all IOAs to all Children
python replicate_custom_ioas.py --config ../config/credentials.json --non-interactive
# Then manually apply to policies as needed via console
```

### Workflow 3: Selective Deployment
```bash
# Replicate specific IOAs to specific Children
python replicate_custom_ioas.py --config ../config/credentials.json
# Select: IOAs 2,5,7
# Select: Children 1,3
# Apply to policies: Yes
```

## Related Documentation

- [../README.md](../README.md) - Main project documentation
- [../CREDENTIALS_GUIDE.md](../CREDENTIALS_GUIDE.md) - Credential configuration guide
- [../INSTALLATION.md](../INSTALLATION.md) - Installation instructions

## Support

For issues or questions:
- Custom IOA API: https://falcon.crowdstrike.com/documentation (Custom IOA Management)
- FalconPy SDK: https://github.com/CrowdStrike/falconpy
- Prevention Policies: https://falcon.crowdstrike.com/documentation (Prevention Policies)

## Example Output Session

```
$ python replicate_custom_ioas.py --config ../config/credentials.json

════════════════════════════════════════════════════════════════════════════════
              FLIGHT CONTROL - CUSTOM IOAs REPLICATOR
════════════════════════════════════════════════════════════════════════════════

Credentials source: Config File

ℹ️ Authenticating to Falcon API...
✓ Authentication successful!

────────────────────────────────────────────────────────────────────────────────
RETRIEVING CUSTOM IOAs
────────────────────────────────────────────────────────────────────────────────
ℹ️ Retrieving Custom IOAs from Parent CID...
✓ Found 5 Custom IOA rule group(s)

ℹ️ Retrieving Child CIDs from Flight Control...
✓ Found 4 child CID(s)

════════════════════════════════════════════════════════════════════════════════
                      SELECT CUSTOM IOAs TO REPLICATE
════════════════════════════════════════════════════════════════════════════════

Available Custom IOAs:

  [1] Lateral Movement Detection (Enabled)
      Description: Detects lateral movement techniques
      ID: abc123...
      Rules: 3

  [2] Credential Access (Enabled)
      Description: Detects credential dumping and theft
      ID: def456...
      Rules: 5

Selection options:
  • Enter IOA numbers separated by commas (e.g., 1,3,5)
  • Enter 'all' to select all Custom IOAs
  • Enter 'q' to quit

Select Custom IOAs to replicate: 1,2
✓ Selected 2 Custom IOA(s):
  • Lateral Movement Detection
  • Credential Access

════════════════════════════════════════════════════════════════════════════════
                    SELECT CHILD CIDs FOR REPLICATION
════════════════════════════════════════════════════════════════════════════════

Available Child CIDs:

  [1] Production Servers
      CID: 6946f672...

  [2] Development Workstations A
      CID: 8cda703d...

Select Child CIDs: 1
✓ Selected 1 Child CID(s):
  • Production Servers

────────────────────────────────────────────────────────────────────────────────
PREVENTION POLICIES
────────────────────────────────────────────────────────────────────────────────

⚠️  Do you want to apply the replicated Custom IOAs to ALL prevention policies in the Child CIDs?

  • This will link each replicated IOA to all prevention policies in each Child CID
  • The IOAs will be enforced on hosts using those policies

Apply to all prevention policies? (yes/no): yes
✓ Will apply IOAs to all prevention policies

════════════════════════════════════════════════════════════════════════════════
                          REPLICATING CUSTOM IOAs
════════════════════════════════════════════════════════════════════════════════

▶ Target: Production Servers
    ⠋ Replicating "Lateral Movement Detection"...
    ✓ Replicated: Lateral Movement Detection
      Applied to 3 prevention policy/policies
    ⠋ Replicating "Credential Access"...
    ✓ Replicated: Credential Access
      Applied to 3 prevention policy/policies
Overall progress [██████████████████████████████] 100% (Production Servers)

╔══════════════════════════════════════════════════════════════════════════════╗
║                         REPLICATION COMPLETE                                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ Custom IOAs replicated:      2                                              ║
║ Child CIDs targeted:          1                                              ║
║ Total operations:             2                                              ║
║ Successful:                   2                                              ║
║ Failed:                       0                                              ║
║ Applied to policies:          Yes                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

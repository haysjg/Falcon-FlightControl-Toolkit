# Interactive Selection Guide

## New Features Added

The `analyze_roles.py` script now supports **interactive selection** of:
1. **Custom roles** to analyze
2. **Child CIDs** to check

## Usage Modes

### Mode 1: Interactive (Default)
Allows you to select specific roles and children to analyze.

```bash
python scripts/analyze_roles.py --config config/credentials.json
```

**Workflow:**
1. Script discovers all custom roles → You select which ones to analyze
2. Script discovers all child CIDs → You select which ones to check
3. Script analyzes only your selections
4. Generates focused reports

### Mode 2: Non-Interactive
Analyzes all roles and all children (original behavior).

```bash
python scripts/analyze_roles.py --config config/credentials.json --non-interactive
```

---

## Interactive Mode Examples

### Example 1: Select Specific Roles and Children

```bash
python scripts/analyze_roles.py --config config/credentials.json
```

**Output:**
```
================================================================================
SELECT CUSTOM ROLES TO ANALYZE
================================================================================

Found 7 custom role(s):

  [1] Custom JIT Requester
  [2] RIL
  [3] VMA-Custom-Role
  [4] VMA-Custom-Host
  [5] mytest1
  [6] mytest2
  [7] Custom JIT Authorizer

Selection options:
  - Enter role numbers separated by commas (e.g., 1,3,5)
  - Enter 'all' to select all custom roles
  - Enter 'q' to quit

Select roles to analyze: 1,7     ← User selects roles 1 and 7

Selected 2 role(s):
  - Custom JIT Requester
  - Custom JIT Authorizer
```

Then:
```
================================================================================
SELECT CHILD CIDs TO CHECK
================================================================================

Found 4 Child CID(s):

  [1] Production Servers
  [2] Development Workstations A
  [3] Development Workstations B
  [4] Enterprise Workstations

Selection options:
  - Enter child numbers separated by commas (e.g., 1,2,4)
  - Enter 'all' to select all children
  - Enter 'q' to quit

Select children to check: 1,2    ← User selects children 1 and 2

Selected 2 child(ren):
  - Production Servers
  - Development Workstations A
```

**Result:** Analyzes only 2 roles × 2 children = 4 checks (instead of 7 × 4 = 28)

---

## Selection Syntax

### For Roles and Children

**Individual selections:**
```
Select roles to analyze: 1
Select roles to analyze: 3
Select roles to analyze: 7
```

**Multiple selections (comma-separated):**
```
Select roles to analyze: 1,3,5
Select roles to analyze: 2,4,6,7
```

**Select all:**
```
Select roles to analyze: all
```

**Cancel/Quit:**
```
Select roles to analyze: q
```

---

## Use Cases

### Use Case 1: Focus on Specific Roles
You only care about JIT roles:
```bash
python scripts/analyze_roles.py --config config/credentials.json

# Select roles: 1,7  (Custom JIT Requester, Custom JIT Authorizer)
# Select children: all
```

### Use Case 2: Check One Child CID
You're setting up a new child and want to see what's missing:
```bash
python scripts/analyze_roles.py --config config/credentials.json

# Select roles: all
# Select children: 3  (Just the new child)
```

### Use Case 3: Audit Specific Combination
Check if production children have security roles:
```bash
python scripts/analyze_roles.py --config config/credentials.json

# Select roles: 2,4,6  (Security-related roles)
# Select children: 1,2  (Production children)
```

### Use Case 4: Full Analysis (Original Behavior)
```bash
python scripts/analyze_roles.py --config config/credentials.json --non-interactive

# No interaction - analyzes everything
```

---

## Benefits of Interactive Mode

✅ **Faster execution** - Only analyze what you need
✅ **Focused reports** - Smaller, more relevant reports
✅ **Better for testing** - Test specific scenarios
✅ **Cost effective** - Fewer API calls
✅ **Flexibility** - Pick and choose what to analyze

---

## Error Handling

### Invalid Selection
```
Select roles to analyze: 99
Warning: Invalid selection 99 (must be between 1 and 7)
No valid roles selected. Please try again.
```

### No Selection
```
Select roles to analyze:
Invalid input. Please enter numbers separated by commas, 'all', or 'q'.
```

### Quit
```
Select roles to analyze: q
Cancelled by user.
```

---

## Tips

### Quick Selections
- `all` - Fastest way to select everything
- `1,2,3` - Consecutive numbers
- `1,4,7` - Skip numbers you don't need

### Planning Your Analysis
1. First run in non-interactive mode to see everything
2. Then use interactive mode to focus on specific areas
3. Use selective analysis for regular checks

### Combining with Environment Variables
```powershell
# Set credentials once
$env:FALCON_CLIENT_ID = "your_id"
$env:FALCON_CLIENT_SECRET = "your_secret"

# Run interactively multiple times
python scripts/analyze_roles.py
python scripts/analyze_roles.py  # Different selections each time
```

---

## Command Line Options Summary

```bash
# Interactive mode (default)
python scripts/analyze_roles.py

# Non-interactive mode (all roles, all children)
python scripts/analyze_roles.py --non-interactive

# With config file
python scripts/analyze_roles.py --config config/credentials.json

# With environment variables
python scripts/analyze_roles.py  # Uses $env:FALCON_CLIENT_ID, etc.

# Custom output directory
python scripts/analyze_roles.py --output-dir custom_reports

# Help
python scripts/analyze_roles.py --help
```

---

## Examples with Full Commands

### PowerShell

**Interactive:**
```powershell
cd API-calls-with-FalconPy
python scripts/analyze_roles.py --config config/credentials.json
# Follow prompts to select roles and children
```

**Non-Interactive:**
```powershell
cd API-calls-with-FalconPy
python scripts/analyze_roles.py --config config/credentials.json --non-interactive
```

**With Environment Variables:**
```powershell
$env:FALCON_CLIENT_ID = "your_id"
$env:FALCON_CLIENT_SECRET = "your_secret"
python scripts/analyze_roles.py
```

---

## Troubleshooting

### Script doesn't prompt for selection
- Check you're not using `--non-interactive` flag
- Make sure you have custom roles (script will show "No custom roles found")

### Can't select multiple items
- Use commas: `1,2,3` not spaces `1 2 3`
- No spaces around commas: `1,2` not `1, 2`

### Want to cancel selection
- Type `q` and press Enter
- Script will exit gracefully

---

## Report Output

Reports generated will only include your selected roles and children:

```
reports/
├── role_analysis_TIMESTAMP.json          # Selected data only
├── role_analysis_TIMESTAMP.txt           # Focused summary
└── manual_replication_guide_TIMESTAMP.md # Customized guide
```

The reports clearly show what was analyzed:
```
Custom roles analyzed: 2  (instead of 7)
Child CIDs checked: 2     (instead of 4)
```

---

## Summary

| Mode           | Roles      | Children   | Use Case                    |
|----------------|------------|------------|----------------------------|
| Interactive    | User picks | User picks | Focused analysis           |
| Non-Interactive| All        | All        | Complete audit             |

**Recommendation:** Start with **non-interactive** to see everything, then use **interactive** for targeted checks!

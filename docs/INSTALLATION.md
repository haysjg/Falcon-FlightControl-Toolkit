# Installation Guide - Analyze Roles FCTL

Quick start guide for setting up and running the Custom Roles Analyzer.

## Prerequisites

- Python 3.9 or higher
- CrowdStrike Falcon API credentials (Client ID and Secret)
- Appropriate API scopes: **User Management Read**

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `crowdstrike-falconpy` - CrowdStrike API SDK
- `python-dotenv` - Environment variable support
- `colorama` - Cross-platform colored terminal output

### 2. Configure Your Credentials

You have **3 options** (choose one):

#### Option A: Config File (Simple)
```bash
# Copy the template
cp config/credentials.json.example config/credentials.json

# Edit with your credentials
# Use your favorite text editor to add:
# - client_id
# - client_secret
# - base_url (usually https://api.crowdstrike.com)
```

#### Option B: Environment Variables (Recommended)
```powershell
# PowerShell
$env:FALCON_CLIENT_ID = "your_client_id_here"
$env:FALCON_CLIENT_SECRET = "your_client_secret_here"
```

```bash
# Bash/Linux/macOS
export FALCON_CLIENT_ID="your_client_id_here"
export FALCON_CLIENT_SECRET="your_client_secret_here"
```

#### Option C: CLI Arguments
```bash
python scripts/analyze_roles.py \
  --client-id "your_client_id" \
  --client-secret "your_client_secret"
```

See **CREDENTIALS_GUIDE.md** for detailed instructions on each method.

### 3. Run the Script

**Interactive Mode (Default):**
```bash
python scripts/analyze_roles.py --config config/credentials.json
```

You'll be prompted to select:
1. Which custom roles to analyze
2. Which child CIDs to check

**Non-Interactive Mode (Analyze All):**
```bash
python scripts/analyze_roles.py --config config/credentials.json --non-interactive
```

## Output

The script generates reports in the `reports/` folder:

- `role_analysis_TIMESTAMP.json` - Detailed JSON data
- `role_analysis_TIMESTAMP.txt` - Human-readable report
- `manual_replication_guide_TIMESTAMP.md` - Step-by-step replication guide

## Troubleshooting

### Authentication Fails
- Verify your Client ID and Secret are correct
- Check that your API credentials have "User Management: Read" scope
- Ensure your base_url matches your Falcon cloud (US-1, US-2, EU-1, etc.)

### Unicode/Emoji Errors on Windows
The script automatically handles this, but if you see encoding errors:
```powershell
# Set console to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### No Colored Output
Colors work automatically on:
- Windows Terminal
- PowerShell
- Command Prompt
- Bash/Linux/macOS terminals

To disable colors:
```bash
$env:NO_COLOR = "1"  # PowerShell
export NO_COLOR=1    # Bash
```

## Next Steps

- Read **README.md** for full feature documentation
- Check **INTERACTIVE_GUIDE.md** for usage examples
- See **VISUAL_OUTPUT_FEATURE.md** for output formatting details

## Support

For issues with:
- **FalconPy SDK**: https://github.com/CrowdStrike/falconpy
- **CrowdStrike API**: https://falcon.crowdstrike.com/documentation

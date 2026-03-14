# Falcon FlightControl Toolkit

Python automation toolkit for CrowdStrike Falcon FlightControl environments using the FalconPy SDK.

---

## ⚠️ Disclaimer

> **IMPORTANT:** This is a **personal contribution** and is **NOT officially supported by CrowdStrike**.
>
> - ❌ **No official support** - These scripts are provided as-is
> - ❌ **Not endorsed** - CrowdStrike does not endorse or maintain this toolkit
> - ✅ **Community-driven** - Personal project for automation purposes
> - ✅ **Use at your own risk** - Test thoroughly in non-production environments first
>
> For official CrowdStrike tools and support, please refer to:
> - **Official API Documentation:** https://falcon.crowdstrike.com/documentation
> - **Official FalconPy SDK:** https://github.com/CrowdStrike/falconpy
> - **CrowdStrike Support:** Contact your CrowdStrike representative

---

## Overview

This toolkit provides enterprise-grade scripts to automate configuration management and replication across Parent and Child CIDs in CrowdStrike Falcon FlightControl environments. All scripts feature interactive modes, visual progress indicators, and comprehensive error handling.

## 🚀 Quick Start with Launcher

The easiest way to use this toolkit is through the **centralized launcher menu**:

```bash
python launcher.py
```

The launcher provides:
- **📋 Categorized Menu** - All scripts organized by function (Replication, Analysis, Export, Testing, Utility)
- **🔄 Automatic Return** - Returns to menu after each script execution
- **⌨️ Simple Navigation** - Just select a number to launch any script
- **🎨 Visual Interface** - Clean, branded interface with JG logo

**No need to remember individual script paths or commands** - just run the launcher and select what you need!

## Available Scripts

### 1. [Custom Roles Analyzer](script_analyze_roles/)

Analyzes custom roles in a Flight Control environment and generates comprehensive reports.

**Quick Start:**
```bash
python script_analyze_roles/analyze_roles.py --config config/credentials.json
```

**Key Features:**
- Interactive role and child CID selection
- Coverage analysis with visual matrix
- Generates JSON, text, and markdown reports
- Manual replication guides for missing roles

**[→ Full Documentation](script_analyze_roles/README.md)**

---

### 2. [Devices & Policies Exporter](script_export_devices_policies/)

Exports devices, host groups, and policies to CSV format for Flight Control CIDs.

**Quick Start:**
```bash
python script_export_devices_policies/export_devices_policies.py --config config/credentials.json
```

**Key Features:**
- Interactive CID selection
- CSV export with 19 columns
- Differentiates Applied vs Assigned policies
- Comprehensive device and policy data

**[→ Full Documentation](script_export_devices_policies/README.md)**

---

### 3. [Custom IOAs Replicator](script_replicate_custom_ioas/)

Replicates Custom IOA (Indicator of Attack) rule groups from Parent CID to Child CIDs.

**Quick Start:**
```bash
python script_replicate_custom_ioas/replicate_custom_ioas.py --config config/credentials.json
```

**Key Features:**
- Interactive IOA and Child CID selection
- Complete rule group replication
- Optional application to prevention policies
- Real-time progress with spinner animations

**[→ Full Documentation](script_replicate_custom_ioas/README.md)**

---

### 4. [Firewall Management Replicator](script_replicate_firewall/) ⭐ NEW

Replicates complete Firewall Management configurations (Policies, Rule Groups, Rules, Network Locations) from Parent CID to Child CIDs in Flight Control environments.

**Quick Start:**
```bash
python script_replicate_firewall/replicate_firewall.py --config config/credentials.json
```

**Key Features:**
- ✅ **Complete Configuration Replication** - Policies, Rule Groups, Rules, and Network Locations
- ✅ **Smart Dependency Resolution** - Automatically replicates all dependencies
- ✅ **Conflict Management** - Interactive handling with Skip/Rename/Overwrite/Skip All options
- ✅ **Preserves Relationships** - Maintains Policy→Rule Group→Rules mappings

**[→ Full Documentation](script_replicate_firewall/README.md)**

---

## Quick Installation

```bash
# Clone the repository
git clone https://github.com/haysjg/Falcon-FlightControl-Toolkit.git
cd Falcon-FlightControl-Toolkit

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp config/credentials.json.example config/credentials.json
# Edit config/credentials.json with your API credentials

# Launch the menu
python launcher.py
```

**[→ Detailed Installation Guide](INSTALLATION.md)**

## Prerequisites

- Python 3.9 or higher
- FalconPy SDK 1.6.0 or higher
- CrowdStrike Falcon API credentials (Client ID and Secret)

### API Scopes by Script

| Script | Required Scopes |
|--------|----------------|
| **analyze_roles.py** | User Management: Read |
| **export_devices_policies.py** | Hosts: Read, Host Groups: Read, Prevention Policies: Read, Response Policies: Read, Sensor Update Policies: Read |
| **replicate_custom_ioas.py** | Custom IOA Rules: Read/Write, Prevention Policies: Read/Write (if applying), Flight Control: Read |
| **replicate_firewall.py** | Firewall Management: Read/Write, Flight Control: Read |

## Credential Configuration

All scripts support **three credential methods** with automatic fallback:

### Method 1: Config File
```bash
cp config/credentials.json.example config/credentials.json
# Edit with your credentials
python <script> --config config/credentials.json
```

### Method 2: Environment Variables (Recommended)
```powershell
# PowerShell
$env:FALCON_CLIENT_ID = "your_client_id"
$env:FALCON_CLIENT_SECRET = "your_client_secret"
python <script>
```

### Method 3: CLI Arguments
```bash
python <script> --client-id "YOUR_ID" --client-secret "YOUR_SECRET"
```

**[→ Complete Credentials Guide](CREDENTIALS_GUIDE.md)**

## Common Features

All scripts in this repository share:

- ✨ **Interactive Mode** - Select specific items to process
- ✨ **Colored Output** - Easy-to-read terminal feedback
- ✨ **Progress Indicators** - Real-time visual progress
- ✨ **Flight Control Support** - Handle Parent and Child CIDs
- ✨ **Multi-Credential Support** - Config file, env vars, or CLI args
- ✨ **Non-Interactive Mode** - Automation-friendly operation

## Project Structure

```
Falcon-FlightControl-Toolkit/
├── launcher.py                   # 🚀 Main menu launcher (START HERE)
├── script_analyze_roles/         # Custom roles analyzer
│   ├── analyze_roles.py          # Main script
│   ├── README.md                 # Detailed documentation
│   ├── INTERACTIVE_GUIDE.md      # Interactive mode guide
│   └── VISUAL_OUTPUT_FEATURE.md  # Visual features docs
├── script_export_devices_policies/ # Device & policy exporter
│   ├── export_devices_policies.py # Main script
│   └── README.md                 # Detailed documentation
├── script_replicate_custom_ioas/ # Custom IOAs replicator
│   ├── replicate_custom_ioas.py  # Main script
│   └── README.md                 # Detailed documentation
├── script_replicate_firewall/    # Firewall config replicator ⭐
│   ├── replicate_firewall.py     # Main script
│   └── README.md                 # Detailed documentation
├── config/                       # Configuration files
│   ├── credentials.json.example  # Template
│   └── credentials.json          # Your credentials (gitignored)
├── docs/                         # Documentation
│   ├── INSTALLATION.md           # Installation guide
│   ├── CREDENTIALS_GUIDE.md      # Credentials setup
│   ├── SECURITY_FIX.md           # Security notes
│   └── tests/                    # Test reports
│       ├── FINAL_VALIDATION_REPORT.md
│       └── FIREWALL_REPLICATION_TEST_REPORT.md
├── tooling/                      # Diagnostic & utility scripts
├── utils/                        # Shared utilities
│   ├── auth.py                   # Authentication helpers
│   └── formatting.py             # Visual formatting
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Usage Examples

### Using the Launcher (Recommended)
```bash
# Start the interactive menu
python launcher.py

# Select a script by number:
# [1] Firewall Management Replication
# [2] Custom IOAs Replication
# [3] Analyze Custom Roles
# [4] Export Devices & Policies
# [5] Generate Firewall Test Data
# [6] Cleanup Firewall Test Data
# [7] Check Current Firewall Data
# [q] Quit
```

### Running Scripts Directly

#### Analyze Custom Roles (Interactive)
```bash
python script_analyze_roles/analyze_roles.py --config config/credentials.json
# Select roles and child CIDs when prompted
```

#### Export All Devices (All CIDs)
```bash
python script_export_devices_policies/export_devices_policies.py \
  --config config/credentials.json \
  --non-interactive
```

#### Use Environment Variables
```powershell
$env:FALCON_CLIENT_ID = "abc123..."
$env:FALCON_CLIENT_SECRET = "xyz789..."
python script_analyze_roles/analyze_roles.py
```

## Documentation

### Script-Specific Documentation
- [script_analyze_roles/README.md](script_analyze_roles/README.md) - Custom roles analyzer
- [script_export_devices_policies/README.md](script_export_devices_policies/README.md) - Devices & policies exporter
- [script_replicate_custom_ioas/README.md](script_replicate_custom_ioas/README.md) - Custom IOAs replicator
- [script_replicate_firewall/README.md](script_replicate_firewall/README.md) - Firewall Management replicator

### General Documentation
- [docs/INSTALLATION.md](docs/INSTALLATION.md) - Installation and setup
- [docs/CREDENTIALS_GUIDE.md](docs/CREDENTIALS_GUIDE.md) - Credential configuration
- [docs/SECURITY_FIX.md](docs/SECURITY_FIX.md) - Security considerations

### Test Reports & Validation
- [docs/tests/FINAL_VALIDATION_REPORT.md](docs/tests/FINAL_VALIDATION_REPORT.md) - Complete validation results
- [docs/tests/FIREWALL_REPLICATION_TEST_REPORT.md](docs/tests/FIREWALL_REPLICATION_TEST_REPORT.md) - Firewall replication tests
- [docs/tests/TESTING_SUMMARY.md](docs/tests/TESTING_SUMMARY.md) - Executive testing summary

### External Resources
- [FalconPy Documentation](https://falconpy.io) - FalconPy SDK docs
- [CrowdStrike API Documentation](https://falcon.crowdstrike.com/documentation) - Falcon API reference

## Support & Resources

- **FalconPy SDK:** https://github.com/CrowdStrike/falconpy
- **FalconPy Wiki:** https://github.com/CrowdStrike/falconpy/wiki
- **CrowdStrike API Docs:** https://falcon.crowdstrike.com/documentation
- **Issues:** https://github.com/haysjg/Falcon-FlightControl-Toolkit/issues

## License

This project is provided as-is for automation purposes.

## ⚠️ Legal Notice

**This toolkit is a personal contribution and is not affiliated with, endorsed by, or supported by CrowdStrike, Inc.**

- The scripts use the official CrowdStrike Falcon API via the FalconPy SDK
- All trademarks and product names are property of their respective owners
- No warranty is provided - use at your own risk
- Always test in non-production environments before deploying

**For official support, contact CrowdStrike directly through your support channels.**

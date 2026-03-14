# Credentials Configuration Guide

## Overview

The scripts in this project support **3 methods** for providing API credentials, with automatic fallback:

1. **Config File** (Highest priority)
2. **CLI Arguments**
3. **Environment Variables** (Automatic fallback)

---

## Method 1: Config File (Recommended for Development)

### Setup
```bash
# Copy the example file
cp config/credentials.json.example config/credentials.json

# Edit with your credentials
# (File is gitignored - never committed)
```

### Usage
```bash
python scripts/analyze_roles.py --config config/credentials.json
```

**Pros:**
- ✅ Easy to use
- ✅ Credentials in one place
- ✅ Automatically gitignored

**Cons:**
- ❌ Stored in plain text
- ❌ Risk if file permissions wrong

---

## Method 2: CLI Arguments (Good for One-Time Use)

### Usage
```bash
python scripts/analyze_roles.py \
  --client-id "your_client_id_here" \
  --client-secret "your_client_secret_here"
```

**Pros:**
- ✅ Explicit and clear
- ✅ No file needed

**Cons:**
- ❌ Credentials in command history
- ❌ Long command line

---

## Method 3: Environment Variables (Recommended for Production)

### PowerShell Setup

**Option A: Current Session Only**
```powershell
# Set variables (valid until you close PowerShell)
$env:FALCON_CLIENT_ID = "your_client_id_here"
$env:FALCON_CLIENT_SECRET = "your_client_secret_here"
$env:FALCON_BASE_URL = "https://api.crowdstrike.com"  # Optional

# Verify
echo $env:FALCON_CLIENT_ID

# Run script (no arguments needed!)
python scripts/analyze_roles.py
```

**Option B: Persistent (All Sessions)**
```powershell
# Set permanently for current user
[System.Environment]::SetEnvironmentVariable('FALCON_CLIENT_ID', 'your_client_id', 'User')
[System.Environment]::SetEnvironmentVariable('FALCON_CLIENT_SECRET', 'your_secret', 'User')

# Restart PowerShell to apply
# Then run:
python scripts/analyze_roles.py
```

**Option C: Using PowerShell Profile (Advanced)**
```powershell
# Edit your profile
notepad $PROFILE

# Add these lines:
$env:FALCON_CLIENT_ID = "your_client_id_here"
$env:FALCON_CLIENT_SECRET = "your_client_secret_here"

# Save and reload
. $PROFILE
```

### CMD (Command Prompt) Setup

**Current Session:**
```cmd
set FALCON_CLIENT_ID=your_client_id_here
set FALCON_CLIENT_SECRET=your_client_secret_here
set FALCON_BASE_URL=https://api.crowdstrike.com

python scripts\analyze_roles.py
```

**Permanent:**
```cmd
setx FALCON_CLIENT_ID "your_client_id_here"
setx FALCON_CLIENT_SECRET "your_client_secret_here"

REM Restart CMD, then:
python scripts\analyze_roles.py
```

### Linux/macOS (Bash/Zsh)

**Current Session:**
```bash
export FALCON_CLIENT_ID="your_client_id_here"
export FALCON_CLIENT_SECRET="your_client_secret_here"
export FALCON_BASE_URL="https://api.crowdstrike.com"

python scripts/analyze_roles.py
```

**Permanent:**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export FALCON_CLIENT_ID="your_client_id_here"' >> ~/.bashrc
echo 'export FALCON_CLIENT_SECRET="your_client_secret_here"' >> ~/.bashrc

# Reload
source ~/.bashrc
```

**Pros:**
- ✅ No plain text files
- ✅ Not in command history
- ✅ Standard practice
- ✅ Works across all scripts automatically

**Cons:**
- ❌ Setup slightly more complex
- ❌ Still in memory (use secure methods for production)

---

## Priority Order (Automatic Fallback)

The scripts automatically check in this order:

```
1. --config file specified?     → Use it
                ↓ No
2. --client-id/secret specified? → Use them
                ↓ No
3. Environment variables set?    → Use them
                ↓ No
4. ERROR: No credentials found!
```

You'll see which method was used:
```
Credentials source: config_file
Credentials source: cli_args
Credentials source: env_vars
```

---

## Examples

### Mix and Match
```bash
# Use env vars for credentials, but override base URL
python scripts/analyze_roles.py --base-url "https://api.eu-1.crowdstrike.com"

# Use config file but override output directory
python scripts/analyze_roles.py --config config/credentials.json --output-dir custom_reports
```

### All Scripts Support This
```bash
# Analyze roles
python scripts/analyze_roles.py

# Replicate roles (interactive)
python scripts/replicate_roles.py

# List devices
python scripts/list_devices.py
```

---

## Security Best Practices

### For Development (Local Machine)
✅ Use **config file** or **environment variables**
✅ Enable BitLocker disk encryption
✅ Use restrictive file permissions

### For Production/Enterprise
✅ Use **environment variables** set by orchestration system
✅ Use secure credential managers:
   - Windows: Credential Manager / Azure Key Vault
   - Linux: systemd-creds / HashiCorp Vault
   - Cloud: AWS Secrets Manager / GCP Secret Manager

### Never
❌ Commit credentials to Git
❌ Share credentials in chat/email
❌ Use production credentials in development
❌ Store in code files

---

## Troubleshooting

### "No credentials found"
```bash
# Check if environment variables are set
# PowerShell:
echo $env:FALCON_CLIENT_ID

# CMD:
echo %FALCON_CLIENT_ID%

# Bash:
echo $FALCON_CLIENT_ID
```

### Environment variables not working
```bash
# PowerShell: Restart your terminal
# OR set them again in current session
```

### Config file not found
```bash
# Check the path
ls config/credentials.json

# Make sure you're in the project directory
pwd  # Should show: .../API-calls-with-FalconPy
```

---

## Quick Start Examples

### First Time Setup (PowerShell)
```powershell
# 1. Set environment variables
$env:FALCON_CLIENT_ID = "your_id"
$env:FALCON_CLIENT_SECRET = "your_secret"

# 2. Test connection
python scripts/analyze_roles.py --output-dir reports

# 3. Check the reports
ls reports/
```

### Daily Use
```powershell
# If env vars are set permanently, just run:
python scripts/analyze_roles.py
```

---

## Summary Table

| Method          | Security | Ease of Use | Best For        |
|----------------|----------|-------------|-----------------|
| Config File    | ⚠️ Low    | ⭐⭐⭐        | Development     |
| CLI Args       | ⚠️ Low    | ⭐⭐          | One-time runs   |
| Env Vars       | ⭐⭐       | ⭐⭐⭐        | Production      |
| Secure Vaults  | ⭐⭐⭐      | ⭐           | Enterprise      |

**Recommendation:** Start with **Method 3 (Environment Variables)** for better security!

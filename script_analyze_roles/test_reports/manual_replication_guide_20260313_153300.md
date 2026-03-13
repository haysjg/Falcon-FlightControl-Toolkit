# Custom Roles Manual Replication Guide

**Generated:** 2026-03-13 15:33:00  
**Parent CID:** `a1b2c3d4e5f6789012345678901234ab`  

## Overview

This guide provides step-by-step instructions to manually replicate custom roles from the Parent CID to Child CIDs in your Flight Control environment.

## Important Notes

- Custom roles **cannot be created via API** in CrowdStrike Falcon
- Roles must be created manually through the Falcon console
- Ensure you have appropriate permissions to manage roles in Child CIDs

## Custom Roles to Replicate

### 1. mytest1

**Description:** Copy of Roles for App Developer  
**Role ID:** `11111111111111111111111111111111`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

### 2. VMA-Custom-Host

**Description:**   
**Role ID:** `22222222222222222222222222222222`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

### 3. Custom JIT Authorizer

**Description:** Temporary additional custom role for JIT Authorizer while OOTB permission can be added to Foundry custom roles  
**Role ID:** `33333333333333333333333333333333`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

### 4. Custom JIT Requester

**Description:** Temporary additional custom role for JIT User & JIT Privileged User while OOTB permission can be added to Foundry custom roles  
**Role ID:** `44444444444444444444444444444444`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

### 5. RIL

**Description:**   
**Role ID:** `55555555555555555555555555555555`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

### 6. VMA-Custom-Role

**Description:**   
**Role ID:** `66666666666666666666666666666666`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

### 7. mytest2

**Description:** Copy of Copy of Roles for App Developer  
**Role ID:** `77777777777777777777777777777777`  
**Permissions Count:** 0  

**✗ Missing in:** Production Servers, Development Workstations A, Development Workstations B, Enterprise Workstations  

⚠️ **Note:** Permissions could not be automatically retrieved. Please review the role in the Parent CID console.

## Step-by-Step Replication Instructions

### For Each Role:

1. **Login to Falcon Console**
   - Navigate to the Parent CID
   - Go to: **Support and resources** > **User management** > **Roles**

2. **Review Role Details**
   - Locate the custom role by name
   - Click to view its permissions
   - Take note of all assigned permissions

3. **Switch to Child CID**
   - Use the CID selector to switch to target Child CID
   - Go to: **Support and resources** > **User management** > **Roles**

4. **Create New Role**
   - Click **Create custom role**
   - Enter the exact role name from Parent
   - Enter the description
   - Assign the same permissions as in Parent
   - Click **Save**

5. **Verify**
   - Confirm the role appears in the Child CID
   - Verify all permissions are correctly assigned

### Repeat for Each Child CID

Use the coverage information above to determine which Child CIDs need each role.

## Replication Checklist

### mytest1

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

### VMA-Custom-Host

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

### Custom JIT Authorizer

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

### Custom JIT Requester

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

### RIL

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

### VMA-Custom-Role

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

### mytest2

- [ ] Production Servers
- [ ] Development Workstations A
- [ ] Development Workstations B
- [ ] Enterprise Workstations

## Additional Resources

- [CrowdStrike Falcon Documentation](https://falcon.crowdstrike.com/documentation)
- [User Management Guide](https://falcon.crowdstrike.com/documentation/84/user-management)
- For detailed permission data, refer to the JSON report


ID: KB-1122
Type: Procedure
Category: Technical
Subcategory: International roaming setup
Title: Technical Procedure: International Roaming Setup Resolution
Tags: international,account,technical,text,international roaming setup,setup,wireless,procedure,roaming
Last Updated: 2024-07-10

---

# Technical Procedure: International Roaming Setup Resolution

## Document Information
**Document ID:** TECH-ROAM-2023-01  
**Last Updated:** [Current Date]  
**Department:** Technical Support  
**Audience:** Tier 1 & 2 Support Agents

## Overview
This procedure guides support agents through diagnosing and resolving international roaming issues for customers. Follow these steps sequentially to efficiently troubleshoot and resolve roaming connectivity problems.

## Required Tools/System Access
- Customer Account Management System (CAMS)
- Network Provisioning Tool (NPT)
- Roaming Partner Database (RPD)
- Device Capability Database (DCD)
- Remote Diagnostic Tool (RDT)
- Ticket Management System

## Procedure

### 1. Initial Assessment

1.1. Verify customer identity using standard authentication protocol.
1.2. Confirm travel details:
   - Current location (country/region)
   - Duration of stay
   - Expected return date
1.3. Verify device information:
   - Make and model
   - IMEI number (dial *#06#)
   - Operating system version
1.4. Check if device is roaming-capable in DCD.
   - If not compatible → Proceed to Section 7 (Device Limitations)

### 2. Account Verification

2.1. Access customer account in CAMS.
2.2. Verify account status is active and in good standing.
   - If account has restrictions → Resolve billing issues before proceeding
2.3. Check if international roaming is enabled on the account.
   - If disabled → Enable roaming feature (requires supervisor approval for accounts <3 months old)
2.4. Verify roaming add-ons/international plans:
   - Document current plan
   - Check for active travel passes/international options
   - Confirm data/voice/text allocations for destination

### 3. Network Provisioning Verification

3.1. Access NPT and check provisioning status.
3.2. Verify HLR (Home Location Register) has proper roaming flags enabled.
3.3. Check for roaming restrictions or blocks.
3.4. Confirm roaming agreements exist for customer's destination in RPD.
   - If no agreement exists → Proceed to Section 8 (Coverage Limitations)

### 4. Device Configuration Diagnostics

4.1. Guide customer to check network settings:
   - **For Android:** Settings → Connections/Network & Internet → Mobile Networks → Network Operators → Select "Automatic"
   - **For iOS:** Settings → Cellular/Mobile Data → Network Selection → Enable "Automatic"
4.2. Verify Data Roaming is enabled:
   - **For Android:** Settings → Connections/Network & Internet → Mobile Networks → Enable "Data Roaming"
   - **For iOS:** Settings → Cellular/Mobile Data → Cellular/Mobile Data Options → Enable "Data Roaming"
4.3. Check APN settings:
   - Use RDT to retrieve correct APN for destination
   - Guide customer through manual APN configuration if needed

### 5. Network Reset Procedure

5.1. Instruct customer to toggle Airplane Mode on for 30 seconds, then off.
5.2. If issue persists, have customer perform device restart.
5.3. Guide customer through network reset:
   - **For Android:** Settings → System → Reset Options → Reset Network Settings
   - **For iOS:** Settings → General → Reset → Reset Network Settings
5.4. After reset, instruct customer to wait 5 minutes for network registration.

### 6. Advanced Troubleshooting

6.1. Use RDT to check device signal and network registration status.
6.2. Verify IMEI is not blocked by international carriers.
6.3. Check for SIM card issues:
   - Confirm SIM is properly inserted
   - Verify SIM is not damaged
   - Consider eSIM provisioning if applicable
6.4. Perform OTA (Over-The-Air) update of device roaming capabilities if available.

## Decision Trees

### 7. Device Limitations Path
7.1. Inform customer of device compatibility issues.
7.2. Offer alternatives:
   - Temporary device rental
   - Local SIM purchase guidance
   - Wi-
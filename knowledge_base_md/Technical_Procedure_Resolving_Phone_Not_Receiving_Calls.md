ID: KB-1175
Type: Procedure
Category: Technical
Subcategory: Phone not receiving calls
Title: Technical Procedure: Resolving Phone Not Receiving Calls
Tags: calls,receiving,technical,phone not receiving calls,procedure,roaming,phone,billing
Last Updated: 2025-03-08

---

# Technical Procedure: Resolving Phone Not Receiving Calls

**Document ID:** TP-CALL-001  
**Last Updated:** [Current Date]  
**Classification:** Internal Support Document  
**Systems Required:** Customer Account Management System (CAMS), Network Diagnostic Tool (NDT), Call Testing Platform (CTP)

## 1. Overview

This procedure guides support agents through diagnosing and resolving instances where customers report their mobile device is not receiving incoming calls. This document follows a systematic approach to identify whether the issue stems from network, device, account, or configuration problems.

## 2. Required Tools/Access

- Customer Account Management System (CAMS) - Level 2 access
- Network Diagnostic Tool (NDT) 
- Call Testing Platform (CTP)
- Device Specifications Database
- Line Test Utility (LTU)

## 3. Initial Assessment

### 3.1 Verify Customer Identity
- Confirm customer identity using standard verification protocol
- Document ticket/case number in CAMS
- Verify device IMEI and SIM ICCID match account records

### 3.2 Gather Initial Information
- Confirm exact symptoms:
  - No calls received at all
  - Some calls received (specific callers/times)
  - Calls go straight to voicemail
  - Calls ring but cannot be answered
- Document when issue began
- Note any recent changes (device updates, SIM changes, location changes)
- Verify if outgoing calls function normally

## 4. Diagnostic Procedure

### 4.1 Account Status Verification
1. Check account status in CAMS
   - Verify account is active and in good standing
   - Check for billing blocks or restrictions
   - Confirm call forwarding settings are disabled
   - Verify no active call barring features

### 4.2 Network Diagnostics
1. Launch Network Diagnostic Tool (NDT)
2. Enter customer's phone number and IMEI
3. Check network registration status
   - If "Not Registered" → Go to Section 5.1
   - If "Registered" → Continue to next step
4. Verify signal strength in customer's area
   - Run coverage analysis using customer's location
   - If signal strength < -100 dBm → Go to Section 5.2
5. Check for network outages or maintenance
   - If active outage → Document outage ticket number and go to Section 7.1

### 4.3 Device Configuration Tests
1. Verify airplane mode is disabled
2. Confirm device is not in Do Not Disturb mode
3. Check call blocking/screening settings
   - iPhone: Settings > Phone > Blocked Contacts/Silence Unknown Callers
   - Android: Phone app > Settings > Blocked numbers
4. Verify third-party call blocking apps are not installed/active
5. Check for active call forwarding
   - iPhone: Settings > Phone > Call Forwarding
   - Android: Phone app > Settings > Calls > Call Forwarding

### 4.4 SIM/Hardware Diagnostics
1. Instruct customer to power cycle device
   - If resolved → Document resolution and close ticket
   - If not resolved → Continue
2. Guide customer through removing and reinserting SIM card
   - If resolved → Document resolution and close ticket
   - If not resolved → Continue
3. Test with alternate SIM if available
   - If alternate SIM works → SIM issue, go to Section 5.3
   - If alternate SIM fails → Continue

### 4.5 Line Test
1. Access Line Test Utility (LTU)
2. Run comprehensive line test to customer's number
3. Analyze results for:
   - Call routing issues
   - Voicemail system errors
   - Network registration problems
   - If issues detected → Document specific error codes and go to Section 5.4

### 4.6 Call Testing
1. Access Call Testing Platform (CTP)
2. Initiate test call to customer's device
3. Document call behavior:
   - Rings but not on customer device
   - Goes directly to voicemail
   - Network busy signal
   - Other behavior

## 5. Resolution Paths

### 5.1 Network Registration Issues
1. Verify SIM is properly provisioned in system
2. Reset network settings on device
   -
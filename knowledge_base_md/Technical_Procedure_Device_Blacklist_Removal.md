ID: KB-1205
Type: Procedure
Category: Technical
Subcategory: Device blacklist removal
Title: Technical Procedure: Device Blacklist Removal
Tags: technical,removal,service,device blacklist removal,procedure,support,device,blacklist
Last Updated: 2024-11-25

---

# Technical Procedure: Device Blacklist Removal
**Document ID:** BL-REM-2023-01  
**Last Updated:** [Current Date]  
**Classification:** Internal Support Document - Level 2 Support

## 1. Overview

This document outlines the procedure for verifying and removing devices from national and carrier blacklists. Blacklisted devices (typically due to reported loss/theft, fraud, or non-payment) are blocked from accessing network services. This procedure helps agents determine eligibility for blacklist removal and execute the removal process when appropriate.

## 2. Required Access/Tools

- Customer account management system (CAMS)
- Device verification portal (DVP)
- National Equipment Identity Register (NEIR) access
- Blacklist management tool (BMT)
- Customer identity verification system
- Case management system
- Proof of purchase documentation review access

## 3. Procedure

### 3.1 Initial Assessment

1. Verify the customer's identity using standard two-factor authentication protocol
   - Photo ID match
   - Account security questions
   - PIN verification

2. Obtain and validate the device IMEI/MEID
   - Request customer to dial *#06# on device
   - Alternatively, check device settings: Settings > About Phone > Status > IMEI Information
   - For non-functional devices, check IMEI on device packaging or purchase receipt

3. Document the blacklist removal request in the case management system
   - Create case ID: format BLR-[customer ID]-[date YYYYMMDD]
   - Note customer's stated reason for blacklist removal

### 3.2 Blacklist Status Verification

1. Check blacklist status in DVP system
   - Enter IMEI/MEID in the search field
   - Document blacklist reason code (see Appendix A for codes)
   - Note blacklist date and originating carrier

2. Determine blacklist type:
   - **Carrier-specific blacklist**: Proceed to section 3.3
   - **National blacklist**: Proceed to section 3.4
   - **International blacklist**: Proceed to section 3.5
   - **No blacklist found**: Troubleshoot using "Device Service Issues" procedure (Doc ID: DSI-2023-05)

### 3.3 Carrier-Specific Blacklist Removal

1. Verify removal eligibility:
   - **Reason code 01-03** (Lost/Stolen): Require proof of recovery documentation
   - **Reason code 04-06** (Non-payment): Verify account standing in CAMS
   - **Reason code 07-09** (Fraud): Check fraud department notes in CAMS

2. If eligible for removal:
   - Access BMT system
   - Select "Carrier Blacklist Management"
   - Enter IMEI/MEID
   - Select "Remove from Blacklist"
   - Enter justification code (see Appendix B)
   - Submit request

3. Verify removal:
   - Wait 10 minutes for system propagation
   - Re-check DVP system to confirm removal
   - If still blacklisted, proceed to section 3.6

### 3.4 National Blacklist Removal

1. Verify removal eligibility:
   - Customer must be original owner (verify purchase documentation)
   - For lost/stolen: require police report showing recovery
   - For non-payment: verify all outstanding balances cleared

2. If eligible:
   - Access NEIR portal
   - Select "Blacklist Management"
   - Enter IMEI/MEID and select "Request Removal"
   - Upload supporting documentation
   - Submit request with justification code

3. Inform customer:
   - National blacklist removal takes 24-48 hours
   - Provide case reference number
   - Schedule follow-up contact

### 3.5 International Blacklist Removal

1. Inform customer:
   - International blacklists require escalation
   - Process may take 5-7 business days
   - Success not guaranteed due to cross-border policies

2. Escalate to International Resolution Team:
   - Complete form IR-2023-BL
   - Attach all supporting documentation
   - Submit via escalation portal
   - Note escalation ID in case management system

###
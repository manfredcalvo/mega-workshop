ID: KB-1014
Type: Procedure
Category: Account
Subcategory: Port-out requirements
Title: Port-Out Management Procedure
Tags: account,requirements,port-out requirements,procedure,roaming,data,phone,port-out
Last Updated: 2024-08-15

---

# Port-Out Management Procedure
**Document ID:** PO-PROC-2023-01  
**Version:** 3.2  
**Last Updated:** October 2023

## 1. Overview

This document outlines the standardized procedure for managing port-out requests from customers wishing to transfer their telephone number(s) to another service provider. Proper handling of these requests is essential for regulatory compliance, customer satisfaction, and prevention of unauthorized transfers.

## 2. Pre-Request Verification

### 2.1 Account Authentication
- Verify customer identity using **at least two** of the following:
  - Account PIN/Password
  - Last 4 digits of SSN/Tax ID
  - Account security questions
  - Two-factor authentication via registered mobile device

### 2.2 Account Status Check
- Confirm account is in good standing
- Verify no outstanding balance exceeding $50
- Check for existing service contracts with early termination fees
- Document any equipment lease/financing agreements

### 2.3 Number Eligibility Verification
- Confirm number(s) are eligible for porting
- Verify number(s) are active on the account
- Check for any temporary suspensions or restrictions
- Validate service address matches CSR (Customer Service Record)

## 3. Port-Out Request Processing

### 3.1 System Documentation
1. Access the Account Management System (AMS)
2. Navigate to "Number Management" → "Port Requests"
3. Create new port-out request record with:
   - Customer account number
   - Telephone number(s) to be ported
   - Receiving carrier information (if available)
   - Customer verification method used
   - Agent ID and timestamp

### 3.2 Port-Out Authorization
1. Generate Port-Out Authorization Code (POA)
2. Document POA in customer account notes using format:
   ```
   PORT-OUT AUTH: [POA CODE]
   VERIFIED BY: [VERIFICATION METHOD]
   AGENT: [AGENT ID]
   TIMESTAMP: [YYYY-MM-DD HH:MM:SS]
   ```
3. Set POA expiration for 30 calendar days

## 4. Compliance Requirements

### 4.1 Regulatory Documentation
- Complete FCC-mandated CPNI (Customer Proprietary Network Information) verification
- Document all verification steps in compliance log
- Record customer consent for number transfer
- Maintain verification records for minimum 2 years

### 4.2 Fraud Prevention Checks
- Flag and escalate if:
  - Account was created within last 30 days
  - Recent account information changes (within 10 days)
  - Multiple port-out attempts within 30-day period
  - Request originates from non-primary account holder
  - Request comes from unrecognized IP address/location

## 5. Customer Notification

### 5.1 Required Notifications
1. Send immediate port-out request confirmation via:
   - SMS to account phone number(s)
   - Email to account email address
   - Push notification to customer's mobile app (if enabled)

2. Notification must include:
   - Port-out request acknowledgment
   - Expected completion timeframe
   - Contact information for questions/concerns
   - Instructions to contact support immediately if unauthorized

### 5.2 Notification Template
```
[COMPANY NAME]: We've received a request to transfer your number(s) [XXX-XXX-XXXX] to another carrier. Expected completion: [DATE]. If you did not authorize this transfer, please contact us immediately at 1-800-XXX-XXXX.
```

## 6. System Updates

### 6.1 Account Status Changes
1. Update account status to "Port-Out Pending"
2. Apply service protection flag to prevent unauthorized changes
3. Document expected port-out date
4. Create follow-up task for port completion verification

### 6.2 Billing System Updates
1. Calculate final bill projection
2. Document any early termination fees
3. Note equipment return requirements
4. Update billing cycle information

## 7. Port Completion

### 7.1 Verification Steps
1. Confirm port completion in Number Portability Administration Center (NPAC)
2. Update internal systems to reflect completed port
3. Document completion date and time
4. Verify final
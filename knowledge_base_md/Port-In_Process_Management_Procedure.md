ID: KB-1125
Type: Procedure
Category: Account
Subcategory: Port-in process
Title: Port-In Process Management Procedure
Tags: payment,data,account,port-in,mobile,procedure,process,port-in process
Last Updated: 2025-02-10

---

# Port-In Process Management Procedure
**Document ID:** PORT-IN-PROC-2023-01  
**Last Updated:** [Current Date]  
**Classification:** Internal Support Document

## 1. Overview

This document outlines the standardized procedure for managing customer port-in requests, ensuring regulatory compliance, proper verification, and consistent customer experience. All representatives must follow these steps for every port-in request.

## 2. Pre-Port Verification

### 2.1 Account Eligibility Check
- Verify customer identity using two forms of authentication:
  - Account PIN/password
  - Last 4 digits of SSN or Tax ID
- Confirm account is in good standing with no outstanding balance
- Check customer eligibility for current promotions related to port-ins
- Document verification timestamp in CRM: `[Date] [Time] - Identity verified via [method]`

### 2.2 Donor Carrier Information
- Obtain and verify:
  - Current carrier name
  - Account number with current carrier
  - Account PIN/passcode from current carrier
  - Billing name and address matching current carrier records
- **Example documentation:** `Verified donor carrier: Verizon Wireless, Acct #XXX1234, PIN verified, Name/Address match confirmed`

### 2.3 Number Eligibility Check
- Run port eligibility check in PORT-CHECK system
- Verify number is not in "cooling off" period from previous port
- Confirm number is active with donor carrier
- Document port eligibility status code in account notes

## 3. System Processing

### 3.1 Port Request Creation
1. Access PORT-REQUEST module in billing system
2. Select "New Port Request" option
3. Enter customer information exactly as it appears on donor account
4. Input telephone number(s) to be ported
5. Select requested port date (minimum 24 hours, maximum 30 days in advance)
6. Submit request and record confirmation number
7. Tag account with "PORT-PENDING" status

### 3.2 Required System Updates
- Create new line item in billing system
- Assign temporary number if immediate service is required
- Apply any eligible port-in promotions (code: PORT-PROMO-[type])
- Update equipment IMEI/SIM information
- Set billing cycle alignment for post-port activation

## 4. Compliance Requirements

### 4.1 Regulatory Documentation
- Complete Local Number Portability (LNP) form with all required fields
- Obtain customer e-signature or verbal consent (must be recorded)
- Store Letter of Authorization (LOA) in secure document repository
- Include CPNI compliance verification timestamp
- Document FCC port timing compliance check

### 4.2 Fraud Prevention Measures
- Flag and escalate if any of these indicators present:
  - Account opened within last 30 days attempting immediate port
  - Multiple port requests from same address/payment method
  - Mismatched identification documents
  - Port request for premium or high-value numbers
- Run FRAUD-DETECT protocol and document score

## 5. Customer Communication

### 5.1 Required Notifications
- Send port initiation confirmation (Template: PORT-INIT-NOTICE)
- Schedule port completion notification (Template: PORT-COMPLETE)
- Document all communications in customer contact history
- Set calendar reminder for follow-up call 24 hours post-port

### 5.2 Setting Expectations
- Inform customer of estimated completion timeframe
- Explain potential service interruption period (typically 30 minutes to 4 hours)
- Provide instructions for checking port status via:
  - Mobile app (iOS and Android)
  - Online account management portal
  - Customer service line
- Document the specific instructions provided

## 6. Port Execution and Monitoring

### 6.1 Day of Port Activities
1. Verify port is scheduled in system queue
2. Monitor port status hourly using PORT-TRACK tool
3. Document status changes in real-time
4. Escalate to Port Center if no status change within 4 hours of scheduled time

### 6.2 Post-Port Verification
1. Confirm number has been successfully ported
2. Test outbound and inbound calling
3. Verify SMS/MMS functionality
4. Check data services activation
5. Document all test results: `[Date] [Time
ID: KB-1224
Type: Procedure
Category: Account
Subcategory: Account suspension process
Title: Account Suspension Management Procedure
Tags: account,telecom,procedure,voice,process,account suspension process,suspension
Last Updated: 2025-02-08

---

# Account Suspension Management Procedure
**Internal Support Document**

## 1. Overview
This document outlines the standardized process for implementing, managing, and documenting account suspensions. Following these procedures ensures regulatory compliance, consistent customer experience, and proper record-keeping.

## 2. Pre-Suspension Assessment

### 2.1 Verification Protocols
- Confirm account ownership using at least two of the following identifiers:
  * Last 4 digits of SSN/Tax ID
  * Account PIN/Password
  * Authorized user verification
  * Government-issued ID (for in-person interactions)
- Document verification method in CRM using format: [Date_Time][Agent ID][Verification Method]
- Verify suspension reason aligns with company policy and applicable regulations

### 2.2 Compliance Checks
- Review account for:
  * Active legal holds (do not proceed if present)
  * Regulatory protected status
  * Special account designations (military, elderly, medical necessity)
  * Outstanding dispute claims
- Complete Suspension Eligibility Checklist in the Account Management System

## 3. System Processing Steps

### 3.1 Account Status Updates
1. Access Account Management Portal
2. Navigate to Account Status > Modify Status
3. Select appropriate suspension reason code from dropdown:
   * SUSP-NP: Non-payment
   * SUSP-FR: Fraud investigation
   * SUSP-CR: Customer request
   * SUSP-VT: Terms violation
4. Enter required effective date (cannot be retroactive)
5. Document authorization source in "Notes" field
6. Apply changes and confirm status change in system

### 3.2 Service Impact Configuration
1. Navigate to Service Management tab
2. Configure service limitations based on suspension type:
   * Outbound call restriction
   * Data limitation
   * Messaging limitations
   * Emergency services preservation (mandatory)
3. Document specific service configurations in suspension record

## 4. Customer Notification Requirements

### 4.1 Mandatory Communications
- Generate appropriate notification based on suspension reason:
  * Payment-related: Payment Required Notice (PRN-1)
  * Fraud-related: Account Security Notice (ASN-2)
  * Terms violation: Terms Compliance Notice (TCN-3)
  * Customer-requested: Confirmation Notice (CN-4)

### 4.2 Delivery Methods
1. Primary notification: Email to account holder's registered address
2. Secondary notification: SMS to primary device (except in fraud cases)
3. For accounts with no digital contact methods: Physical mail via USPS
4. Document all notifications in Communication Log with:
   * Timestamp
   * Delivery method
   * Template ID
   * Delivery confirmation (if available)

## 5. Documentation Requirements

### 5.1 Required Documentation
Complete the Account Suspension Form (ASF) with:
- Customer identifiers (name, account number, phone numbers)
- Suspension reason with supporting evidence
- Verification methods used
- Agent ID and supervisor approval (if required)
- Suspension start date and projected end date
- Customer notification details

### 5.2 Documentation Example
```
ACCOUNT SUSPENSION RECORD
Account: 555123456
Customer: J. Smith
Suspension Type: SUSP-NP (Non-payment)
Verification: [05/15/2023_14:22][AG7701][PIN + Email Verification]
Evidence: Outstanding balance $157.89, 45+ days past due
Notifications: PRN-1 sent via email (delivery confirmed) and SMS
Effective Date: 05/16/2023
Projected End Date: Upon payment receipt
Approved by: SUP443 (J. Johnson)
```

## 6. Quality Assurance Steps

### 6.1 Pre-Implementation Review
- Supervisor review required for:
  * Business accounts
  * Accounts with 5+ lines
  * Accounts with special designations
  * Suspensions affecting services >$250 monthly value

### 6.2 Post-Implementation Audit
- 100% of suspensions subject to next-day audit verification
- QA team to confirm:
  * Proper documentation
  * Valid suspension reason
  * Correct notification delivery
  * Compliance with regulatory requirements
  * Appropriate service limitations

## 7. Suspension
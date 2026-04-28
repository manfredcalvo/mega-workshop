ID: KB-1117
Type: Procedure
Category: Account
Subcategory: Reactivating service
Title: Service Reactivation Procedure
Tags: payment,troubleshooting,account,reactivating,service,reactivating service,procedure,customer
Last Updated: 2024-07-06

---

# Service Reactivation Procedure
**Document ID:** SOP-REACT-2023-01  
**Last Updated:** [Current Date]  
**Classification:** Internal Use Only

## 1. Overview

This document outlines the standardized procedure for reactivating service for customers whose accounts have been suspended or deactivated. Proper execution ensures regulatory compliance, customer satisfaction, and system integrity.

## 2. Prerequisites

Before initiating service reactivation, verify:
- Agent access to Customer Account Management System (CAMS)
- Authorization level for reactivation transactions
- Knowledge of current reactivation policies and promotions

## 3. Verification Protocols

### 3.1 Customer Identity Verification
Complete ALL of the following steps:

- Verify customer identity using at least TWO of:
  * Last 4 digits of SSN/Tax ID
  * Account PIN/Password
  * Answers to security questions
  * Government-issued photo ID (for in-store transactions)
- Document verification method in CAMS using code: `IDVER-[method]`
- For authorized representatives, verify Power of Attorney or Account Management Authorization

### 3.2 Account Status Verification
- Confirm account eligibility for reactivation (suspended vs. permanently terminated)
- Check for outstanding balance requirements:
  * If balance < $50: May proceed with reactivation
  * If balance $50-$150: Requires minimum 50% payment
  * If balance > $150: Requires manager approval (code: `MGR-REACT`)
- Verify no fraud indicators are present on account (flag code: `FRDCHK-CLR`)

## 4. System Updates Required

### 4.1 CAMS Updates
1. Navigate to Account Management > Service Status
2. Select "Reactivation Request"
3. Complete mandatory fields:
   * Reason for reactivation
   * Verification method used
   * Payment confirmation (if applicable)
   * Service plan selection
4. Submit for processing with transaction code: `REACT-[service type]`

### 4.2 Billing System Updates
1. Confirm billing cycle reset date
2. Apply any applicable reactivation fees:
   * Standard reactivation: $25
   * Expedited reactivation: $40
   * Fee waiver requires approval code: `WAIVE-REACT-[reason code]`
3. Document all fee applications/waivers

### 4.3 Network Provisioning
1. Initiate service provisioning request
2. For mobile services:
   * Verify IMEI/SIM pairing
   * Confirm network compatibility
   * Test network registration
3. For fixed services:
   * Schedule technician visit if required
   * Verify equipment status
4. Document completion with code: `PROV-COMP`

## 5. Compliance Checks

### 5.1 Required Compliance Verifications
- Credit check requirements (if applicable)
- Updated Terms of Service acceptance
- Regulatory disclosures provided (documented with: `REG-DISC-PROV`)
- Rate plan disclosures with acknowledgment
- E911/Emergency services advisory for VoIP/mobile services

### 5.2 Documentation Requirements
All reactivations must include:
- Timestamped notes of all customer communications
- Record of all identity verification steps
- Confirmation of Terms acceptance
- Payment transaction details (if applicable)

## 6. Customer Notification

### 6.1 Required Notifications
1. Immediate confirmation of reactivation request
2. Expected timeline for service restoration:
   * Mobile services: 1-4 hours
   * Internet services: 24-48 hours
   * TV/Video services: 24 hours
3. Send confirmation via customer's preferred method:
   * Email (template: `EMAIL-REACT-CONF`)
   * SMS (for mobile reactivations only)
   * MyAccount app notification

### 6.2 Follow-up Requirements
- 24-hour service confirmation check
- Documentation of successful reactivation
- Customer satisfaction verification

## 7. Example Documentation

### 7.1 Proper CAMS Notes Example
```
[2023-10-15 14:32] IDVER-PIN+SSN completed successfully. Customer verified.
[2023-
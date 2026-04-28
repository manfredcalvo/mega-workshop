ID: KB-1177
Type: Procedure
Category: Technical
Subcategory: Esim activation issues
Title: Technical Procedure: Resolving eSIM Activation Issues
Tags: activation,technical,service,telecom,esim activation issues,procedure,roaming,esim,issues
Last Updated: 2024-06-27

---

# Technical Procedure: Resolving eSIM Activation Issues

## Document ID: TP-ESIM-001
## Version: 2.3
## Last Updated: [Current Date]

### Overview
This procedure guides support agents through diagnosing and resolving eSIM activation issues. Follow these steps sequentially unless directed otherwise by the decision tree.

### Required Access/Tools
- Customer account management system (CAMS)
- eSIM provisioning platform (EPP)
- Network diagnostics tool (NDT)
- QR code generation system
- Knowledge base access
- Customer verification protocols

### Prerequisites
- Verified customer identity per security protocol SP-ID-100
- Confirmed device IMEI number
- Confirmed device eSIM compatibility (reference device compatibility database)

## Diagnostic Procedure

### 1. Initial Assessment
1. Verify customer account status in CAMS
   - Confirm account is active and in good standing
   - Verify eSIM service is included in customer plan
   - Check for any pending orders or recent changes

2. Verify device eligibility
   - Confirm device model supports eSIM technology
   - Check if device is carrier-locked
   - Verify device OS meets minimum requirements:
     * iOS: 12.1 or later
     * Android: 10 or later (varies by manufacturer)

3. Determine activation method previously attempted
   - QR code scan
   - Manual activation
   - App-based activation
   - Carrier app installation

### 2. System Validation
1. Check eSIM provisioning status in EPP
   - Status should be one of: "Pending," "Active," "Failed," or "Not Initiated"
   - Note error codes if present

2. Verify EID (eSIM identifier) in system
   - Confirm EID matches device
   - Check for duplicate EID registrations

3. Run network diagnostics using NDT
   - Verify IMSI is correctly mapped to customer profile
   - Check for network registration attempts
   - Verify APN settings are correctly provisioned

## Troubleshooting Decision Tree

### A. If Status = "Not Initiated"
1. Initiate new eSIM profile in EPP
2. Generate new QR code
3. Guide customer through activation process
4. Proceed to Verification (Step 5)

### B. If Status = "Pending"
1. Check timestamp of pending status
   - If <30 minutes: Ask customer to wait, explain processing time
   - If >30 minutes: Proceed to step 2
2. Reset eSIM status in EPP to "Not Initiated"
3. Follow path A (Not Initiated)

### C. If Status = "Failed"
1. Document specific error code: _________
2. Reference error code in technical manual TM-ESIM-ERR
3. Based on error code:
   
   | Error Code | Action |
   |------------|--------|
   | E-1001 to E-1010 | Reset profile and regenerate QR code |
   | E-2001 to E-2015 | Check device settings and retry |
   | E-3001 to E-3020 | Network issue - proceed to Network Troubleshooting |
   | E-4001+ | Requires escalation |

4. If error persists after recommended action, proceed to Escalation

### D. If Status = "Active" but service not working
1. Verify device settings:
   - Cellular data is enabled
   - eSIM is set as primary line (if applicable)
   - Data roaming is enabled (if applicable)
2. Reset network settings on device
3. If issue persists, proceed to Network Troubleshooting

## 4. Network Troubleshooting
1. Verify signal strength in customer's location
2. Check for network outages in customer's area
3. Reset network connection on server side:
   - Access NDT
   - Select "Reset Connection" for customer IMSI
   - Wait 2 minutes for reset to complete
4. Guide customer to reset network settings:
   - iOS: Settings > General > Reset > Reset Network Settings
   - Android: Settings > System > Reset options > Reset Wi-Fi, mobile & Bluetooth

## 5. Verification
1. Confirm eSIM shows as active
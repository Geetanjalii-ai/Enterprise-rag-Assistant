# VPN & Zero Trust Access Guide

**Company:** Meridian Software Services Pvt. Ltd.  
**Document ID:** IT-HOW-002  
**Title:** VPN Setup Guide  
**Version:** 2.0  
**Effective date:** 2026-11-01  
**Owner:** Information Technology  
**Applies to:** All employees  

## Overview & Architecture

Meridian has transitioned from legacy client VPN to Meridian Zero Trust Network Access (ZTNA) powered by WireGuard. All remote employees must authenticate through the Meridian Cloud Gateway to access internal repositories, staging clusters, and departmental portals.

## Quick Setup Instructions

1. **Download Gateway Client:** Open Company Portal (Windows) or Managed Self-Service (macOS) and install `Meridian Zero Trust Client v2.0`.
2. **Biometric & Passkey Login:** Open the client and authenticate with your corporate work email (`username@company.com`). Tap your hardware FIDO2 security key or use Windows Hello / Touch ID biometric authentication.
3. **Gateway Verification:** The status will turn green (`Zero Trust Tunnel: Active`).

## Traffic Routing & Split Tunneling

- **Corporate Traffic:** Only internal subnet traffic (`10.240.0.0/16` and `*.meridian.internal`) is routed through the encrypted enterprise gateway tunnel.
- **Direct Internet Access:** Zoom, Google Meet, YouTube, and generic web browsing automatically bypass the VPN tunnel, preserving low latency and high bandwidth.

## Support & Emergency Access

If you encounter authentication failures or hardware key sync issues:
- Raise a high-priority ticket on the IT Service Desk: `https://it-support.meridian.internal`.
- For emergency lockouts during off-hours, call the IT Hotline at extension `5555` (toll-free: `+1-800-555-MERIDIAN`).

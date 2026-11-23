# Admin Runbook: User Account Management

**Company:** Meridian Software Services Pvt. Ltd.  
**Document ID:** IT-RUN-001  
**Version:** 1.1  
**Effective date:** 2026-01-10  
**Owner:** Information Technology  
**Applies to:** IT administrators  

## Purpose

Steps for IT administrators to create, change and disable user accounts in the Meridian directory. Follow every step and record it in the ticket.

## Create an account for a new joiner

1. Confirm the joining ticket is approved by HR.
2. Create the user in the directory with the format firstname.lastname@meridian.example.
3. Add the user to the department group and to the all-staff group.
4. Issue a temporary password and require a change at first sign-in.
5. Enforce MFA enrolment at first sign-in.
6. Record the account in the ticket and notify the hiring manager.

## Change of department

Remove the user from the old department group and add the new one on the effective date given by HR. Review and remove any special access from the old role.

## Disable an account when someone leaves

1. HR raises an exit ticket with the last working day.
2. Disable the account within 1 hour of the end of the last working day.
3. Revoke all active sessions and remove MFA devices.
4. Convert the mailbox to a shared mailbox for the manager and retain it for 90 days.
5. Delete the account after 90 days unless Legal asks for it to be kept.

## Privileged access

- Admin rights need written approval from the IT Manager.
- Privileged accounts are separate from the daily-use account.
- Access reviews are run every quarter and results are saved in the audit folder.

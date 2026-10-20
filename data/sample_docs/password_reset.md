# Password Reset and Account Lockout Procedures

**Source:** IT Support Knowledge Base  
**Document ID:** KB-AUTH-001  
**Category:** Account Access and Authentication  
**Last reviewed:** 2024-01-15

---

## Overview

This document describes the self-service and helpdesk-assisted procedures for resetting
passwords and unlocking accounts on the corporate identity system. Passwords and passphrases
must never be shared verbally or in writing.

---

## Account lockout policy

The corporate policy locks an account after **5 consecutive failed login attempts**.
The lockout duration is **30 minutes** before automatic release, or immediately upon IT
helpdesk intervention.

Note: Lockouts are counted per-account, not per-device. Logging in from a different device
will not bypass the lockout.

---

## Self-service password reset (SSPR)

If you have previously registered for self-service reset:

1. Navigate to the corporate SSPR portal at the URL provided by IT during onboarding.
2. Enter your corporate email address.
3. Choose a verification method: authenticator app, email to your registered personal
   address, or SMS to your registered phone number.
4. Follow the prompts to set a new password.
5. The new password must meet the corporate complexity requirements:
   - Minimum 12 characters
   - At least one uppercase letter, one lowercase letter, one digit, and one special
     character
   - Must not match any of the last 10 passwords
6. After reset, sign out of all sessions and sign in with the new password.

---

## Helpdesk-assisted reset

If SSPR is unavailable or you have not registered:

1. Contact the IT helpdesk by phone or in-person. Do not request password resets by email
   or chat, as identity cannot be verified securely through those channels.
2. The helpdesk agent will verify your identity using your employee ID and at least one
   additional factor (security questions, manager confirmation, or government-issued ID).
3. The agent will issue a temporary password. You must change it at next login.
4. Temporary passwords expire after **8 hours**.

---

## If the account is locked but the password is correct

1. Wait 30 minutes for the lockout to clear automatically.
2. Check whether any service, mobile app, or scheduled task is repeatedly attempting to
   authenticate with an old password. Update the saved credentials in those services.
3. If the lockout recurs immediately after clearing: contact the helpdesk, as a background
   process may be causing repeated failures.

---

## Escalation

Escalate to the identity and access management team if:
- The account cannot be unlocked after helpdesk intervention.
- Multiple accounts are locked simultaneously (may indicate a password-spray attack).
- A user suspects their credentials have been compromised.

---

## Security reminders

- Never share your password with anyone, including IT staff.
- IT staff will never ask for your current password.
- Use the corporate password manager to store credentials securely.
- Enable multi-factor authentication on all accounts that support it.

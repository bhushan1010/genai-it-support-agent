# VPN Connection Failure Troubleshooting Guide

**Source:** IT Support Knowledge Base  
**Document ID:** KB-NET-002  
**Category:** Network and Connectivity  
**Last reviewed:** 2024-01-15

---

## Overview

This guide covers common VPN connection failures for users working remotely. The corporate
VPN allows secure access to internal resources. Do not attempt to bypass VPN by using
unapproved tunnelling or proxy services.

---

## Common error messages and causes

| Error message | Likely cause |
|---|---|
| "Authentication failed" | Incorrect credentials or expired MFA token |
| "Unable to contact server" | No internet connection or VPN server is unreachable |
| "Connection timed out" | Firewall blocking VPN traffic or server overload |
| "Certificate error" | VPN client certificate is expired or missing |
| "Client software out of date" | VPN client version is not compatible with server |

---

## Step 1 — Verify internet connectivity

Before connecting to VPN, confirm you have internet access:

1. Open a browser and navigate to a public site such as `example.com`.
2. If you have no internet: troubleshoot your connection first (see KB-NET-001).
3. VPN cannot connect without a working internet connection.

## Step 2 — Confirm credentials

1. Use your corporate username (firstname.lastname format) and current password.
2. If MFA is required: approve the push notification in your authenticator app within
   60 seconds. If the notification does not arrive, use the TOTP code instead.
3. Do not enter the MFA code in the password field.

## Step 3 — Check the VPN client version

1. Open the VPN client application.
2. Navigate to **Help → About** and note the version number.
3. Compare against the approved version listed in the IT portal.
4. If out of date: download the current version from the internal software portal or
   request an update from IT.

## Step 4 — Clear VPN client cache

1. Disconnect and close the VPN client.
2. In Windows, navigate to `%APPDATA%\VPNClient` (replace VPNClient with your client
   folder name) and delete the `cache` subfolder.
3. Restart the VPN client and reconnect.

## Step 5 — Check the VPN server address

1. Open the VPN client settings.
2. Confirm the server address matches the address published in the IT portal.
3. Do not change the server address without IT confirmation.

## Step 6 — Check local firewall settings

1. Open **Windows Defender Firewall with Advanced Security**.
2. Confirm that the VPN client application is in the allowed applications list.
3. VPN typically requires UDP ports 500 and 4500 (IKEv2) or TCP port 443 (SSL VPN).
4. If you are on a public Wi-Fi network (hotel, airport): some networks block VPN traffic
   and cannot be resolved by the user. Contact IT for alternative access options.

---

## Escalation

Escalate to the network team if:
- The server address is confirmed correct but the connection still fails.
- The client certificate has expired (visible in the error log).
- Multiple users report simultaneous VPN failures (possible server issue).

When escalating, provide: VPN client version, operating system version, error message text,
and VPN client log file (Help → Export Logs in most clients).

---

## Security notes

- Always use the corporate VPN when accessing internal resources remotely.
- Do not split-tunnel all traffic through a personal VPN while also connected to the
  corporate VPN, as this may violate security policy.
- Report any unexpected VPN disconnections to IT immediately.

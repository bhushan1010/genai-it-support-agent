# Wi-Fi Connectivity Troubleshooting Guide

**Source:** IT Support Knowledge Base  
**Document ID:** KB-NET-001  
**Category:** Network and Connectivity  
**Last reviewed:** 2024-01-15

---

## Overview

This guide covers the most common causes of Wi-Fi connectivity failures on corporate-managed
laptops and desktops. Follow the steps in order. Do not skip steps.

---

## Step 1 — Confirm the problem scope

- Check whether other devices on the same network (phone, colleague laptop) can connect.
- If no device can connect: the access point or the broader network may be down. Report to
  the network team and skip to the Escalation section.
- If only your device cannot connect: continue to Step 2.

## Step 2 — Check the wireless adapter

1. Press **Windows + X** and select **Device Manager**.
2. Expand **Network Adapters**.
3. Look for a yellow warning icon on the Wi-Fi adapter.
4. If a warning icon is present: right-click the adapter and select **Update driver** →
   **Search automatically for updated drivers**.
5. If the adapter is missing entirely: the driver may be corrupted. Reinstall the driver from
   the manufacturer's support site.

## Step 3 — Forget and reconnect to the network

1. Click the Wi-Fi icon in the taskbar.
2. Click the arrow next to the network name → **Forget**.
3. Wait 10 seconds, then reconnect and enter the passphrase.
4. If you do not know the passphrase: contact the IT helpdesk. Passphrases are not stored
   in tickets or email.

## Step 4 — Flush DNS and reset the TCP/IP stack

Open **Command Prompt as Administrator** and run the following commands one at a time:

```
ipconfig /flushdns
netsh int ip reset
netsh winsock reset
```

Restart the computer after running these commands.

## Step 5 — Check IP address assignment

1. Open Command Prompt and run `ipconfig /all`.
2. Confirm that the IPv4 address is in the expected subnet (e.g., 192.168.x.x or 10.x.x.x)
   and not 169.254.x.x (APIPA — means DHCP failed).
3. If the address is 169.254.x.x: the device is not receiving a DHCP lease.
   - Try running `ipconfig /release` then `ipconfig /renew`.
   - If this fails, report to the network team.

## Step 6 — Check firewall and VPN software

- Some third-party firewalls or VPN clients can block Wi-Fi when active.
- Temporarily disable the VPN client and test connectivity.
- Do not disable the corporate firewall permanently.

---

## Escalation

Escalate to the network team if:
- Multiple devices are affected.
- The issue persists after all steps above.
- You suspect an access-point hardware failure.
- The IP address cannot be renewed.

When escalating, provide: device hostname, MAC address (from `ipconfig /all`), and the
error messages observed.

---

## Prevention

- Keep wireless drivers updated via Windows Update.
- Report intermittent connectivity early before it becomes a persistent failure.
- Do not modify TCP/IP settings without IT approval.

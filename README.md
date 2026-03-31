[# campus_connect_care
A campus network monitoring system for common network faults and that provides guided troubleshooting.](https://github.com/SourAvCoder441/campus_connect_care

# Campus Connect‑Care – Network Diagnostic Tool

A campus network monitoring system that detects common network faults and provides guided troubleshooting. Developed and validated in a **virtual lab environment** (GNS3 + VMware) but fully compatible with **real physical network setups** running pfSense, Open vSwitch (or any SSH‑accessible managed switch), and standard IP subnets.

## 🚀 Features

- On‑demand full diagnosis or network scan
- Detects **IP conflicts**, **network loops**, **high latency**, **packet loss**, **DHCP exhaustion**, **bandwidth saturation**, and **cable failures**
- Discovers devices and maps them to switch ports (including unmanaged switches)
- Generates plain‑English troubleshooting steps for each fault
- Maintains historical diagnostic sessions in a PostgreSQL database

## 🔧 Requirements (for both virtual and real networks)

| Component               | Role                                                                 |
|-------------------------|----------------------------------------------------------------------|
| **pfSense firewall** (or any Linux firewall with SSH) | Provides DHCP, ARP tables, and gateway IPs. Must be reachable via SSH. |
| **Managed switch** (Open vSwitch, Cisco, etc.) | Provides MAC address table via SSH (commands: `ovs-appctl fdb/show`, `brctl showmacs`, or equivalent). |
| **Master PC**           | Runs the diagnostic tool. Requires Python 3.10+, network access to firewall and switches. |
| **Client devices**      | Any number of end devices (PCs, printers, cameras) in different subnets. |

> ✅ The tool was **tested extensively in a GNS3/VMware virtual lab**, but it works identically on a real campus network – as long as SSH credentials and IP addresses are correctly configured.

## 📦 Installation

### 1. Clone the repository

``bash
git clone https://github.com/SourAvCoder441/campus_connect_care.git
cd campus_connect_care)
 
### 2. Create a virtual environment (recommended)

``bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate



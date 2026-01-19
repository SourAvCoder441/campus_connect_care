import subprocess

PFSENSE_IP = "192.168.1.1"
PFSENSE_USER = "admin"

def allow_client(ip):
    subprocess.run([
        "ssh",
        f"{PFSENSE_USER}@{PFSENSE_IP}",
        f"pfctl -t allowed -T add {ip}"
    ])

def block_client(ip):
    subprocess.run([
        "ssh",
        f"{PFSENSE_USER}@{PFSENSE_IP}",
        f"pfctl -t allowed -T delete {ip}"
    ])

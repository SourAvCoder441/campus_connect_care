#!/usr/bin/env python3
"""
Network Loop Detector
Detects network loops using multi-factor analysis
Based on net_loop1.py but uses database for configuration
"""

import re
import time
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import Fault, FAULT_NETWORK_LOOP


class NetworkLoopDetector(BaseDetector):
    """Detect network loops in switches"""
    
    # Thresholds
    THRESHOLDS = {
        'mac_flap_count': 3,      # MAC moves between ports
        'broadcast_rate': 1000,    # packets per second
        'mac_table_size': 200,     # entries
        'cpu_percent': 80,         # CPU utilization
        'error_count': 100,        # RX errors
        'sampling_window': 5,      # seconds
        'sample_interval': 1,       # seconds between samples
    }
    
    # Scoring weights
    WEIGHTS = {
        'mac_flapping': 40,
        'broadcast_storm': 30,
        'mac_table_growth': 20,
        'cpu_spike': 10,
        'interface_errors': 10,
    }
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.samples = []  # Time-series samples
        self.loop_detected = False
        self.confidence = 0
        self.score = 0
        
    def collect_samples(self, switch_ip: str) -> List[Dict]:
        """Collect metrics samples over time window"""
        samples = []
        duration = self.THRESHOLDS['sampling_window']
        interval = self.THRESHOLDS['sample_interval']
        
        self.log(f"Collecting samples from {switch_ip} for {duration}s...")
        
        for i in range(duration):
            sample = {
                'timestamp': time.time(),
                'mac_table': self.get_mac_table(switch_ip),
                'interface_stats': self.get_interface_stats(switch_ip),
                'cpu_percent': self.get_cpu_usage(switch_ip),
            }
            samples.append(sample)
            
            if i < duration - 1:
                time.sleep(interval)
        
        return samples
    
    def get_mac_table(self, switch_ip: str) -> Dict[str, Dict]:
        """Get MAC table from switch"""
        ssh = self.ssh_connections.get(switch_ip)
        if not ssh:
            return {}
        
        # Find switch info
        switch_info = next((s for s in self.switches if s['ip'] == switch_ip), None)
        if not switch_info:
            return {}
        
        if 'Open' in switch_info['type'] or 'ovs' in switch_info['type'].lower():
            output = self.ssh_exec(switch_ip,
                                  f"sudo ovs-appctl fdb/show br0",
                                  use_sudo=True)
        else:
            output = self.ssh_exec(switch_ip, "brctl showmacs br0")
        
        mac_table = {}
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                if 'Open' in switch_info['type']:
                    mac_candidate = parts[2]
                else:
                    mac_candidate = parts[1]
                
                if re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', mac_candidate, re.I):
                    mac = mac_candidate.lower()
                    port = parts[0] if 'Open' in switch_info['type'] else parts[3]
                    age = parts[3] if 'Open' in switch_info['type'] else '0'
                    
                    mac_table[mac] = {
                        'port': port,
                        'age': int(age) if age.isdigit() else 0
                    }
        
        return mac_table
    
    def get_interface_stats(self, switch_ip: str) -> Dict[str, Dict]:
        """Get interface statistics from switch"""
        output = self.ssh_exec(switch_ip, "cat /proc/net/dev")
        
        stats = {}
        for line in output.splitlines():
            match = re.match(r'^\s*(\w+):\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', line)
            if match:
                iface = match.group(1)
                if iface != 'lo':
                    stats[iface] = {
                        'rx_bytes': int(match.group(2)),
                        'rx_packets': int(match.group(3)),
                        'rx_errors': int(match.group(4)),
                        'rx_dropped': int(match.group(5)),
                        'tx_bytes': int(match.group(10)),
                        'tx_packets': int(match.group(11)),
                        'tx_errors': int(match.group(12)),
                        'tx_dropped': int(match.group(13)),
                    }
        
        return stats
    
    def get_cpu_usage(self, switch_ip: str) -> float:
        """Get CPU usage percentage"""
        output = self.ssh_exec(switch_ip, "top -bn1 | head -3")
        
        # Try to parse CPU usage
        for line in output.split('\n'):
            if '%Cpu' in line:
                match = re.search(r'(\d+\.\d+)\s*id', line)
                if match:
                    idle = float(match.group(1))
                    return round(100 - idle, 1)
        
        return 0.0
    
    def analyze_mac_flapping(self, samples: List[Dict]) -> Tuple[bool, int]:
        """Detect MAC flapping (same MAC on different ports)"""
        mac_port_history = defaultdict(list)
        
        for sample in samples:
            for mac, info in sample['mac_table'].items():
                mac_port_history[mac].append(info['port'])
        
        flap_count = 0
        for mac, ports in mac_port_history.items():
            unique_ports = set(ports)
            if len(unique_ports) > 1:
                flap_count += len(unique_ports) - 1
        
        detected = flap_count >= self.THRESHOLDS['mac_flap_count']
        return detected, flap_count
    
    def analyze_broadcast_storm(self, samples: List[Dict]) -> Tuple[bool, float]:
        """Detect broadcast storm by packet rate"""
        if len(samples) < 2:
            return False, 0.0
        
        total_packets_start = 0
        total_packets_end = 0
        
        for iface, stats in samples[0]['interface_stats'].items():
            total_packets_start += stats['rx_packets']
        
        for iface, stats in samples[-1]['interface_stats'].items():
            total_packets_end += stats['rx_packets']
        
        time_delta = samples[-1]['timestamp'] - samples[0]['timestamp']
        if time_delta <= 0:
            return False, 0.0
        
        packet_delta = total_packets_end - total_packets_start
        rate = packet_delta / time_delta
        
        # Estimate broadcast rate (typically 10-30% of total in storm)
        estimated_broadcast_rate = rate * 0.2
        detected = estimated_broadcast_rate > self.THRESHOLDS['broadcast_rate']
        
        return detected, round(estimated_broadcast_rate, 1)
    
    def analyze_mac_table_growth(self, samples: List[Dict]) -> Tuple[bool, int]:
        """Detect abnormal MAC table growth"""
        last_table = samples[-1]['mac_table'] if samples else {}
        table_size = len(last_table)
        
        detected = table_size > self.THRESHOLDS['mac_table_size']
        return detected, table_size
    
    def analyze_cpu(self, samples: List[Dict]) -> Tuple[bool, float]:
        """Detect CPU spike"""
        cpu_values = [s['cpu_percent'] for s in samples if s['cpu_percent'] > 0]
        
        if not cpu_values:
            return False, 0.0
        
        avg_cpu = sum(cpu_values) / len(cpu_values)
        detected = avg_cpu > self.THRESHOLDS['cpu_percent']
        
        return detected, round(avg_cpu, 1)
    
    def analyze_interface_errors(self, samples: List[Dict]) -> Tuple[bool, int]:
        """Detect interface errors"""
        if len(samples) < 2:
            return False, 0
        
        total_errors_start = 0
        total_errors_end = 0
        
        for iface, stats in samples[0]['interface_stats'].items():
            total_errors_start += stats['rx_errors'] + stats['tx_errors']
        
        for iface, stats in samples[-1]['interface_stats'].items():
            total_errors_end += stats['rx_errors'] + stats['tx_errors']
        
        error_delta = total_errors_end - total_errors_start
        detected = error_delta > self.THRESHOLDS['error_count']
        
        return detected, error_delta
    
    def calculate_score(self, metrics: Dict) -> int:
        """Calculate detection score based on weighted factors"""
        score = 0
        
        if metrics.get('mac_flapping_detected'):
            score += self.WEIGHTS['mac_flapping']
        if metrics.get('broadcast_storm_detected'):
            score += self.WEIGHTS['broadcast_storm']
        if metrics.get('mac_table_growth_detected'):
            score += self.WEIGHTS['mac_table_growth']
        if metrics.get('cpu_spike_detected'):
            score += self.WEIGHTS['cpu_spike']
        if metrics.get('interface_errors_detected'):
            score += self.WEIGHTS['interface_errors']
        
        return score
    
    def check_switch_for_loop(self, switch_ip: str) -> Optional[Fault]:
        """Check a single switch for loops"""
        self.log(f"Checking switch {switch_ip} for loops...")
        
        # Connect to switch
        switch_info = next((s for s in self.switches if s['ip'] == switch_ip), None)
        if not switch_info:
            return None
        
        if not self.ssh_connect(switch_ip, switch_info['username'], switch_info['password']):
            return None
        
        # Collect samples
        samples = self.collect_samples(switch_ip)
        
        if not samples:
            return None
        
        # Analyze each factor
        metrics = {}
        
        metrics['mac_flapping_detected'], metrics['mac_flap_count'] = self.analyze_mac_flapping(samples)
        metrics['broadcast_storm_detected'], metrics['broadcast_rate'] = self.analyze_broadcast_storm(samples)
        metrics['mac_table_growth_detected'], metrics['mac_table_size'] = self.analyze_mac_table_growth(samples)
        metrics['cpu_spike_detected'], metrics['cpu_percent'] = self.analyze_cpu(samples)
        metrics['interface_errors_detected'], metrics['error_count'] = self.analyze_interface_errors(samples)
        
        # Calculate score
        score = self.calculate_score(metrics)
        
        # Determine confidence
        if score >= 70:
            confidence = "HIGH"
        elif score >= 40:
            confidence = "MEDIUM"
        else:
            confidence = "NONE"
        
        self.log(f"Switch {switch_ip} loop score: {score}/100 ({confidence})")
        
        if confidence in ["HIGH", "MEDIUM"]:
            # Loop detected
            steps = self.get_troubleshooting_steps('NETWORK_LOOP')
            
            evidence = {
                'switch_ip': switch_ip,
                'score': score,
                'confidence': confidence,
                'metrics': metrics,
                'thresholds': self.THRESHOLDS
            }
            
            fault = Fault(
                session_id=self.session_id,
                fault_type='NETWORK_LOOP',
                severity='critical',
                description=f"Network loop detected on switch {switch_ip} (confidence: {confidence})",
                affected_ips=[],
                evidence=evidence,
                troubleshooting_steps=steps
            )
            
            return fault
        
        return None
    
    def detect(self) -> List[Fault]:
        """Check all switches for network loops"""
        self.log("=" * 60)
        self.log("NETWORK LOOP DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        for switch in self.switches:
            try:
                fault = self.check_switch_for_loop(switch['ip'])
                if fault:
                    faults.append(fault)
                    self.add_fault(
                        'NETWORK_LOOP', 'critical',
                        f"Network loop detected on switch {switch['ip']}",
                        evidence={'switch': switch['ip'], 'score': fault.evidence.get('score')},
                        troubleshooting_steps=fault.troubleshooting_steps
                    )
            except Exception as e:
                self.log(f"Error checking switch {switch['ip']}: {e}", 'ERROR')
        
        self.log(f"Network loop detection complete: {len(faults)} faults")
        return faults

#!/usr/bin/env python3
"""
High Latency Detector
Measures latency to all gateway interfaces (including VLANs)
Based on hld_1.py but uses database for configuration
"""

import re
import time
from typing import Dict, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import Fault, FAULT_HIGH_LATENCY


class HighLatencyDetector(BaseDetector):
    """Detect high latency to gateways and critical devices"""
    
    THRESHOLDS = {
        'warning': 10,    # ms average
        'critical': 50,   # ms average
    }
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.targets = []  # List of targets to test
        
    def discover_targets(self) -> List[Dict]:
        """Discover all gateway interfaces to test"""
        targets = []
        
        # Add firewall gateways
        for iface in self.firewall_interfaces:
            if iface['ip'] and iface['ip'] != '0.0.0.0':
                # Skip loopback
                if iface['ip'].startswith('127.'):
                    continue
                
                target = {
                    'name': iface['type'],
                    'ip': iface['ip'],
                    'type': 'gateway',
                    'subnet': iface['subnet'],
                    'description': f"{iface['type']} on {iface['name']}"
                }
                
                # Add VLAN info if applicable
                if iface.get('vlan_id'):
                    target['name'] = f"{iface['type']}_VLAN{iface['vlan_id']}"
                    target['description'] = f"VLAN {iface['vlan_id']} on {iface.get('parent', 'unknown')}"
                
                targets.append(target)
        
        # Add switches
        for switch in self.switches:
            targets.append({
                'name': f"Switch_{switch['ip']}",
                'ip': switch['ip'],
                'type': 'switch',
                'subnet': switch.get('subnet', 'unknown'),
                'description': f"Managed switch ({switch['type']})"
            })
        
        # Add master PC itself
        if self.master_pc['ip']:
            targets.append({
                'name': 'Master_PC',
                'ip': self.master_pc['ip'],
                'type': 'master',
                'description': 'Master PC (local)'
            })
        
        self.log(f"Discovered {len(targets)} targets for latency testing")
        return targets
    
    def ping_target(self, target: Dict, count: int = 5) -> Dict:
        """
        Ping a target multiple times and calculate statistics
        """
        ip = target['ip']
        
        try:
            # Run ping with specified count
            import subprocess
            result = subprocess.run(
                ['ping', '-c', str(count), '-i', '0.2', ip],
                capture_output=True,
                text=True,
                timeout=count + 2
            )
            
            output = result.stdout
            
            # Parse packet loss
            loss_match = re.search(r'(\d+)% packet loss', output)
            loss_percent = float(loss_match.group(1)) if loss_match else 100.0
            
            # Parse ping statistics
            rtt_match = re.search(r'rtt min/avg/max/\w+ = ([\d.]+)/([\d.]+)/([\d.]+)', output)
            
            if rtt_match and loss_percent < 100:
                min_ms = float(rtt_match.group(1))
                avg_ms = float(rtt_match.group(2))
                max_ms = float(rtt_match.group(3))
                
                # Determine status
                if loss_percent > 5:
                    status = 'CRITICAL'
                    message = f"Packet loss: {loss_percent}%"
                elif avg_ms >= self.THRESHOLDS['critical']:
                    status = 'CRITICAL'
                    message = f"High latency: {avg_ms:.2f}ms"
                elif avg_ms >= self.THRESHOLDS['warning']:
                    status = 'WARNING'
                    message = f"Elevated latency: {avg_ms:.2f}ms"
                else:
                    status = 'OK'
                    message = f"Normal: {avg_ms:.2f}ms"
                
                return {
                    'ip': ip,
                    'reachable': True,
                    'loss_percent': loss_percent,
                    'min_ms': min_ms,
                    'avg_ms': avg_ms,
                    'max_ms': max_ms,
                    'status': status,
                    'message': message
                }
            else:
                # No response
                status = 'CRITICAL' if loss_percent > 0 else 'UNKNOWN'
                return {
                    'ip': ip,
                    'reachable': False,
                    'loss_percent': 100.0,
                    'status': status,
                    'message': 'No response'
                }
                
        except Exception as e:
            return {
                'ip': ip,
                'reachable': False,
                'loss_percent': 100.0,
                'status': 'ERROR',
                'message': str(e)
            }
    
    def detect(self) -> List[Fault]:
        """Test latency to all discovered targets"""
        self.log("=" * 60)
        self.log("HIGH LATENCY DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        # Discover targets
        self.targets = self.discover_targets()
        
        self.log(f"Testing latency to {len(self.targets)} targets...")
        
        # Test targets in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_target = {
                executor.submit(self.ping_target, target, count=10): target
                for target in self.targets
            }
            
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result(timeout=15)
                    
                    # Check for high latency
                    if result['status'] in ['WARNING', 'CRITICAL']:
                        steps = self.get_troubleshooting_steps('HIGH_LATENCY')
                        
                        fault = Fault(
                            session_id=self.session_id,
                            fault_type='HIGH_LATENCY',
                            severity='high' if result['status'] == 'CRITICAL' else 'medium',
                            description=f"{result['status']}: {target['name']} ({target['ip']}) - {result['message']}",
                            affected_ips=[target['ip']],
                            evidence={
                                'target': target,
                                'result': result,
                                'thresholds': self.THRESHOLDS
                            },
                            troubleshooting_steps=steps
                        )
                        faults.append(fault)
                        
                        self.add_fault(
                            'HIGH_LATENCY',
                            'high' if result['status'] == 'CRITICAL' else 'medium',
                            f"{result['status']} latency to {target['name']}: {result.get('avg_ms', 0):.2f}ms",
                            affected_ips=[target['ip']],
                            evidence=result
                        )
                        
                        self.log(f"  {result['status']}: {target['name']} - {result.get('avg_ms', 0):.2f}ms")
                    else:
                        self.log(f"  OK: {target['name']} - {result.get('avg_ms', 0):.2f}ms")
                        
                except Exception as e:
                    self.log(f"  Error testing {target['name']}: {e}", 'ERROR')
        
        self.log(f"High latency detection complete: {len(faults)} faults")
        return faults

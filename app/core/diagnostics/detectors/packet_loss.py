#!/usr/bin/env python3
"""
Packet Loss Detector
Detects packet loss to critical network targets
Based on PL_1.py but uses database for configuration
"""

import re
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.models import Fault, FAULT_PACKET_LOSS, FAULT_DEVICE_UNREACHABLE


class PacketLossDetector(BaseDetector):
    """Detect packet loss to critical network devices"""
    
    THRESHOLDS = {
        'warning': 1.0,   # % loss
        'critical': 5.0,  # % loss
    }
    
    def __init__(self, session_id: int):
        super().__init__(session_id)
        self.targets = []
        
    def discover_targets(self) -> List[Dict]:
        """Discover critical targets to test"""
        targets = []
        
        # Add all gateways
        for iface in self.firewall_interfaces:
            if iface['ip'] and iface['ip'] != '0.0.0.0' and not iface['ip'].startswith('127.'):
                targets.append({
                    'name': f"Gateway_{iface['type']}",
                    'ip': iface['ip'],
                    'type': 'gateway',
                    'criticality': 'high'
                })
        
        # Add all switches
        for switch in self.switches:
            targets.append({
                'name': f"Switch_{switch['ip']}",
                'ip': switch['ip'],
                'type': 'switch',
                'criticality': 'high'
            })
        
        # Add master PC
        if self.master_pc['ip']:
            targets.append({
                'name': 'Master_PC',
                'ip': self.master_pc['ip'],
                'type': 'master',
                'criticality': 'high'
            })
        
        # Sample some end devices from DHCP (optional)
        # This would require getting recent devices from diagnostic_devices
        
        self.log(f"Discovered {len(targets)} targets for packet loss testing")
        return targets
    
    def test_target(self, target: Dict, count: int = 20) -> Dict:
        """Test packet loss to a single target"""
        ip = target['ip']
        
        try:
            import subprocess
            result = subprocess.run(
                ['ping', '-c', str(count), '-i', '0.2', ip],
                capture_output=True,
                text=True,
                timeout=count + 2
            )
            
            output = result.stdout
            
            # Parse packet statistics
            stats_match = re.search(r'(\d+) packets transmitted, (\d+) received, ([\d.]+)% packet loss', output)
            if stats_match:
                sent = int(stats_match.group(1))
                received = int(stats_match.group(2))
                loss_percent = float(stats_match.group(3))
                lost = sent - received
            else:
                sent = count
                received = 0
                loss_percent = 100.0
                lost = count
            
            # Parse latency
            rtt_match = re.search(r'rtt min/avg/max/\w+ = ([\d.]+)/([\d.]+)/([\d.]+)', output)
            if rtt_match:
                avg_latency = float(rtt_match.group(2))
            else:
                avg_latency = 0
            
            # Determine status
            if loss_percent >= self.THRESHOLDS['critical']:
                status = 'CRITICAL'
                message = f"Severe loss: {loss_percent}% ({lost}/{sent})"
            elif loss_percent >= self.THRESHOLDS['warning']:
                status = 'WARNING'
                message = f"Elevated loss: {loss_percent}% ({lost}/{sent})"
            elif loss_percent > 0:
                status = 'WARNING'
                message = f"Minor loss: {loss_percent}%"
            else:
                status = 'OK'
                message = f"Normal: 0% loss, {avg_latency:.2f}ms avg"
            
            return {
                'target': target,
                'reachable': received > 0,
                'sent': sent,
                'received': received,
                'lost': lost,
                'loss_percent': loss_percent,
                'avg_latency': avg_latency,
                'status': status,
                'message': message
            }
            
        except Exception as e:
            return {
                'target': target,
                'reachable': False,
                'sent': count,
                'received': 0,
                'lost': count,
                'loss_percent': 100.0,
                'status': 'ERROR',
                'message': str(e)
            }
    
    def detect(self) -> List[Fault]:
        """Test packet loss to all targets"""
        self.log("=" * 60)
        self.log("PACKET LOSS DETECTOR")
        self.log("=" * 60)
        
        faults = []
        
        # Discover targets
        self.targets = self.discover_targets()
        
        self.log(f"Testing packet loss to {len(self.targets)} targets...")
        
        # Test targets in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_target = {
                executor.submit(self.test_target, target): target
                for target in self.targets
            }
            
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result(timeout=30)
                    
                    if result['status'] in ['WARNING', 'CRITICAL']:
                        steps = self.get_troubleshooting_steps('PACKET_LOSS')
                        
                        fault = Fault(
                            session_id=self.session_id,
                            fault_type='PACKET_LOSS',
                            severity='high' if result['status'] == 'CRITICAL' else 'medium',
                            description=f"{result['status']}: Packet loss to {target['name']} ({target['ip']}) - {result['message']}",
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
                            'PACKET_LOSS',
                            'high' if result['status'] == 'CRITICAL' else 'medium',
                            f"{result['status']} packet loss to {target['name']}: {result['loss_percent']}%",
                            affected_ips=[target['ip']],
                            evidence=result
                        )
                        
                        self.log(f"  {result['status']}: {target['name']} - {result['loss_percent']}% loss")
                        
                        # If completely unreachable, also add unreachable fault
                        if result['received'] == 0:
                            steps_unreach = self.get_troubleshooting_steps('DEVICE_UNREACHABLE')
                            fault2 = Fault(
                                session_id=self.session_id,
                                fault_type='DEVICE_UNREACHABLE',
                                severity='critical',
                                description=f"Device unreachable: {target['name']} ({target['ip']})",
                                affected_ips=[target['ip']],
                                evidence=result,
                                troubleshooting_steps=steps_unreach
                            )
                            faults.append(fault2)
                    else:
                        self.log(f"  OK: {target['name']} - {result['loss_percent']}% loss")
                        
                except Exception as e:
                    self.log(f"  Error testing {target['name']}: {e}", 'ERROR')
        
        self.log(f"Packet loss detection complete: {len(faults)} faults")
        return faults

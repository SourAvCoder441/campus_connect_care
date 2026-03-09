#!/usr/bin/env python3
"""
Detector Manager - Runs all detectors and coordinates results
"""

import time
from typing import List, Dict, Optional, Type
from datetime import datetime

from app.core.diagnostics.base_detector import BaseDetector
from app.core.diagnostics.database import DiagnosticDB
from app.core.diagnostics.models import DiagnosticSession, Fault


class DetectorManager:
    """Manages all diagnostic detectors"""
    
    # Available detectors
    DETECTORS = {
        'device_discovery': 'app.core.diagnostics.detectors.device_discovery.DeviceDiscoveryDetector',
        'ip_conflict': 'app.core.diagnostics.detectors.ip_conflict.IPConflictDetector',
        'network_loop': 'app.core.diagnostics.detectors.network_loop.NetworkLoopDetector',
        'high_latency': 'app.core.diagnostics.detectors.high_latency.HighLatencyDetector',
        'packet_loss': 'app.core.diagnostics.detectors.packet_loss.PacketLossDetector',
        'dhcp_exhaustion': 'app.core.diagnostics.detectors.dhcp_exhaustion.DHCPExhaustionDetector',
        'bandwidth': 'app.core.diagnostics.detectors.bandwidth.BandwidthDetector',
        'topology': 'app.core.diagnostics.detectors.topology.TopologyDetector'
    }
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.session_id = None
        self.detectors = []
        self.faults = []
        self.start_time = None
    
    def create_session(self, scan_type: str = 'full',
                       target_subnet: Optional[str] = None,
                       target_device: Optional[str] = None) -> int:
        """Create a new diagnostic session"""
        self.session_id = DiagnosticDB.create_session(
            self.user_id, scan_type, target_subnet, target_device
        )
        self.start_time = time.time()
        return self.session_id
    
    def run_detectors(self, detector_names: List[str]) -> List[Fault]:
        """
        Run specified detectors
        detector_names: list of keys from DETECTORS dict
        """
        if not self.session_id:
            raise ValueError("No session created. Call create_session first.")
        
        all_faults = []
        
        for name in detector_names:
            if name not in self.DETECTORS:
                print(f"Warning: Unknown detector {name}")
                continue
            
            # Import detector class
            module_path, class_name = self.DETECTORS[name].rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            detector_class = getattr(module, class_name)
            
            # Create and run detector
            detector = detector_class(self.session_id)
            print(f"\n▶ Running {detector_class.__name__}...")
            
            try:
                faults = detector.detect()
                all_faults.extend(faults)
                print(f"  ✓ Found {len(faults)} issues")
                
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                DiagnosticDB.log_event('ERROR', detector_class.__name__,
                                      f"Detection failed: {str(e)}",
                                      session_id=self.session_id)
            finally:
                detector.disconnect_all()
        
        self.faults = all_faults
        return all_faults
    
    def run_all(self) -> List[Fault]:
        """Run all available detectors"""
        return self.run_detectors(list(self.DETECTORS.keys()))
    
    def run_quick(self) -> List[Fault]:
        """Run only essential detectors for quick check"""
        quick_detectors = ['device_discovery', 'ip_conflict', 'packet_loss']
        return self.run_detectors(quick_detectors)
    
    def run_performance(self) -> List[Fault]:
        """Run only performance-related detectors"""
        perf_detectors = ['high_latency', 'packet_loss', 'bandwidth']
        return self.run_detectors(perf_detectors)
    
    def complete_session(self, summary: Optional[str] = None):
        """Complete the diagnostic session"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        # Update session stats
        DiagnosticDB.log_event('INFO', 'DetectorManager',
                              f"Diagnostic completed in {elapsed:.1f} seconds",
                              session_id=self.session_id)
        
        DiagnosticDB.complete_session(self.session_id, summary)
    
    def fail_session(self, error: str):
        """Mark session as failed"""
        DiagnosticDB.fail_session(self.session_id, error)
    
    def get_results(self) -> Dict:
        """Get all results for the session"""
        return DiagnosticDB.get_session_results(self.session_id)

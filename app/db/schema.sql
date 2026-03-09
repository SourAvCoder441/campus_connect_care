CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(30) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_session (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Network Setup Tables
CREATE TABLE IF NOT EXISTS network_setup (
    id SERIAL PRIMARY KEY,
    setup_completed BOOLEAN DEFAULT FALSE,
    master_pc_ip VARCHAR(45),
    master_pc_interface VARCHAR(50),
    gateway_ip VARCHAR(45),
    diagnostic_interface VARCHAR(50),
    diagnostic_ip VARCHAR(45),
    switch_sudo_password TEXT,
    setup_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Single table for ALL interfaces (including VLANs)
CREATE TABLE IF NOT EXISTS firewall_interfaces (
    id SERIAL PRIMARY KEY,
    interface_name VARCHAR(50) NOT NULL,
    interface_type VARCHAR(20) NOT NULL,
    ip_address VARCHAR(45),
    subnet_mask VARCHAR(15),
    is_dhcp_enabled BOOLEAN DEFAULT FALSE,
    subnet_cidr VARCHAR(20),
    parent_interface VARCHAR(50),  -- For VLANs: em3
    vlan_id INTEGER,                -- For VLANs: 20, 50
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS managed_switches (
    id SERIAL PRIMARY KEY,
    subnet_id INTEGER REFERENCES firewall_interfaces(id) ON DELETE CASCADE,
    switch_ip VARCHAR(45) NOT NULL,
    switch_type VARCHAR(50),
    ssh_username VARCHAR(50),
    ssh_password_encrypted TEXT,
    port_mapping JSONB,
    last_seen TIMESTAMP,
    sudo_password TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_firewall_interfaces_type ON firewall_interfaces(interface_type);
CREATE INDEX IF NOT EXISTS idx_firewall_interfaces_parent ON firewall_interfaces(parent_interface);
CREATE INDEX IF NOT EXISTS idx_managed_switches_subnet ON managed_switches(subnet_id);

-- ============================================
-- DIAGNOSTIC SYSTEM TABLES - ADD TO EXISTING SCHEMA
-- ============================================

-- 1. Diagnostic Sessions
CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',
    scan_type VARCHAR(20) NOT NULL,
    target_subnet VARCHAR(45),
    target_device VARCHAR(45),
    summary TEXT,
    
    -- Statistics
    total_devices_found INTEGER DEFAULT 0,
    total_faults_detected INTEGER DEFAULT 0,
    critical_faults INTEGER DEFAULT 0,
    high_faults INTEGER DEFAULT 0,
    medium_faults INTEGER DEFAULT 0,
    low_faults INTEGER DEFAULT 0,
    info_faults INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Discovered Devices (per session)
CREATE TABLE IF NOT EXISTS diagnostic_devices (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    
    -- Device identification
    hostname VARCHAR(100),
    ip_address VARCHAR(45) NOT NULL,
    mac_address VARCHAR(17),
    subnet VARCHAR(45),
    
    -- Switch information
    switch_ip VARCHAR(45),
    switch_port VARCHAR(20),
    port_age VARCHAR(20),
    
    -- Status and confidence
    status VARCHAR(20) NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    evidence_sources TEXT[],
    
    -- Evidence details
    in_dhcp BOOLEAN DEFAULT FALSE,
    in_arp BOOLEAN DEFAULT FALSE,
    responds_to_ping BOOLEAN DEFAULT FALSE,
    in_mac_table BOOLEAN DEFAULT FALSE,
    
    -- Additional info
    device_type VARCHAR(50),
    manufacturer VARCHAR(100),
    open_ports INTEGER[],
    response_time_ms FLOAT,
    
    -- Timestamps
    first_seen TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_diag_devices_session ON diagnostic_devices(session_id);
CREATE INDEX IF NOT EXISTS idx_diag_devices_ip ON diagnostic_devices(ip_address);
CREATE INDEX IF NOT EXISTS idx_diag_devices_mac ON diagnostic_devices(mac_address);

-- 3. Fault Categories (pre-populated)
CREATE TABLE IF NOT EXISTS fault_categories (
    id SERIAL PRIMARY KEY,
    fault_name VARCHAR(100) UNIQUE NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    troubleshooting_steps TEXT[] NOT NULL,
    detection_rule TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Detected Faults
CREATE TABLE IF NOT EXISTS detected_faults (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    
    -- Fault identification
    fault_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    
    -- Affected devices
    primary_device_id INTEGER REFERENCES diagnostic_devices(id) ON DELETE CASCADE,
    secondary_device_id INTEGER REFERENCES diagnostic_devices(id),
    affected_ips TEXT[],
    affected_macs TEXT[],
    
    -- Description and evidence
    description TEXT NOT NULL,
    evidence JSONB,
    confidence FLOAT DEFAULT 1.0,
    
    -- Troubleshooting
    troubleshooting_steps TEXT[] NOT NULL,
    
    -- Resolution tracking
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by INTEGER REFERENCES users(id),
    resolution_notes TEXT,
    
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_faults_session ON detected_faults(session_id);
CREATE INDEX IF NOT EXISTS idx_faults_severity ON detected_faults(severity);

-- 5. Network Statistics (per session)
CREATE TABLE IF NOT EXISTS network_statistics (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    subnet VARCHAR(45),
    
    total_devices INTEGER DEFAULT 0,
    active_devices INTEGER DEFAULT 0,
    powered_off_devices INTEGER DEFAULT 0,
    cable_failures INTEGER DEFAULT 0,
    new_devices INTEGER DEFAULT 0,
    removed_devices INTEGER DEFAULT 0,
    
    ip_conflicts INTEGER DEFAULT 0,
    network_loops INTEGER DEFAULT 0,
    high_latency_devices INTEGER DEFAULT 0,
    packet_loss_devices INTEGER DEFAULT 0,
    dhcp_exhaustion INTEGER DEFAULT 0,
    bandwidth_saturation INTEGER DEFAULT 0,
    
    avg_response_time_ms FLOAT,
    scan_duration_seconds INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Enhanced System Logs
CREATE TABLE IF NOT EXISTS system_logs (
    id SERIAL PRIMARY KEY,
    log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    log_level VARCHAR(20) NOT NULL,
    component VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    session_id INTEGER REFERENCES diagnostic_sessions(id),
    message TEXT NOT NULL,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for logs
CREATE INDEX IF NOT EXISTS idx_logs_time ON system_logs(log_time);
CREATE INDEX IF NOT EXISTS idx_logs_level ON system_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_logs_session ON system_logs(session_id);

-- 7. Device History
CREATE TABLE IF NOT EXISTS device_history (
    id SERIAL PRIMARY KEY,
    device_id INTEGER REFERENCES diagnostic_devices(id) ON DELETE CASCADE,
    session_id INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    
    status VARCHAR(20),
    switch_port VARCHAR(20),
    response_time_ms FLOAT,
    open_ports INTEGER[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Troubleshooting Actions
CREATE TABLE IF NOT EXISTS troubleshooting_actions (
    id SERIAL PRIMARY KEY,
    fault_id INTEGER REFERENCES detected_faults(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    
    action_taken TEXT NOT NULL,
    was_successful BOOLEAN,
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INSERT FAULT CATEGORIES (Run once)
-- ============================================

INSERT INTO fault_categories (fault_name, severity, description, troubleshooting_steps) VALUES
-- Critical faults
('IP_CONFLICT', 'critical', 
 'Multiple devices using the same IP address causing network instability',
 ARRAY[
   'Step 1: Identify all devices with conflicting IP (check ARP table)',
   'Step 2: Check DHCP server logs for duplicate lease assignments',
   'Step 3: Verify if any devices have static IPs in DHCP range',
   'Step 4: Change IP of one conflicting device temporarily',
   'Step 5: For static devices, assign unique IP outside DHCP range',
   'Step 6: For DHCP devices, add MAC reservation',
   'Step 7: Clear ARP cache on firewall after changes'
 ]),

('NETWORK_LOOP', 'critical',
 'Network loop detected - excessive broadcast traffic, high switch CPU',
 ARRAY[
   'Step 1: Identify switch where loop originates (check MAC table flapping)',
   'Step 2: Look for redundant cabling between switches',
   'Step 3: Verify Spanning Tree Protocol (STP) is enabled',
   'Step 4: Check for ports with high broadcast/multicast traffic',
   'Step 5: Temporarily disable suspect ports one by one',
   'Step 6: Once loop resolved, reconfigure cabling',
   'Step 7: Enable loop protection features (BPDU guard)'
 ]),

('DEVICE_UNREACHABLE', 'critical',
 'Device does not respond to ICMP ping',
 ARRAY[
   'Step 1: Check if device is powered on (LED indicators)',
   'Step 2: Verify network cable is connected securely',
   'Step 3: Check switch port status - is it up/down?',
   'Step 4: Verify VLAN configuration on switch port',
   'Step 5: Check for IP address conflicts',
   'Step 6: Try pinging from different source',
   'Step 7: Replace cable if suspecting physical issue'
 ]),

-- High severity
('CABLE_FAILURE', 'high',
 'Network cable is disconnected or faulty',
 ARRAY[
   'Step 1: Check physical connection at device side',
   'Step 2: Check physical connection at switch side',
   'Step 3: Verify link LEDs on both switch port and device NIC',
   'Step 4: Try different cable if available',
   'Step 5: Check switch port configuration - administratively down?',
   'Step 6: Check for port errors using switch commands',
   'Step 7: Try different switch port'
 ]),

('HIGH_LATENCY', 'high',
 'Network latency exceeds normal thresholds',
 ARRAY[
   'Step 1: Check for bandwidth saturation on links',
   'Step 2: Verify no network loops causing congestion',
   'Step 3: Check for faulty hardware (cables, ports)',
   'Step 4: Monitor for unusual traffic patterns',
   'Step 5: Check if latency is consistent or intermittent',
   'Step 6: Verify QoS configurations if applicable',
   'Step 7: Consider upgrading link capacity if persistent'
 ]),

('PACKET_LOSS', 'high',
 'Significant packet loss detected',
 ARRAY[
   'Step 1: Check physical layer (cables, connections)',
   'Step 2: Verify switch port for errors (CRC, collisions)',
   'Step 3: Check for bandwidth saturation',
   'Step 4: Verify no IP conflicts causing issues',
   'Step 5: Test with different cable/port',
   'Step 6: Check for electromagnetic interference',
   'Step 7: Monitor for patterns (time of day, specific traffic)'
 ]),

('DHCP_EXHAUSTION', 'high',
 'DHCP pool is nearly or completely exhausted',
 ARRAY[
   'Step 1: Check current DHCP pool utilization',
   'Step 2: Identify devices with static IPs in DHCP range',
   'Step 3: Consider expanding DHCP pool size',
   'Step 4: Check for unauthorized devices consuming addresses',
   'Step 5: Review lease times - consider reducing',
   'Step 6: Implement DHCP reservations for critical devices',
   'Step 7: Plan for subnet expansion if consistently full'
 ]),

('BANDWIDTH_SATURATION', 'high',
 'Network link is saturated (>80% utilization)',
 ARRAY[
   'Step 1: Identify top talkers using switch statistics',
   'Step 2: Check what applications are consuming bandwidth',
   'Step 3: Verify if legitimate large transfers are happening',
   'Step 4: Scan for malware causing abnormal traffic',
   'Step 5: Implement QoS to prioritize critical traffic',
   'Step 6: Consider link aggregation or upgrade',
   'Step 7: Schedule large transfers during off-peak hours'
 ]),

-- Medium severity
('SWITCH_PORT_ERRORS', 'medium',
 'Switch port showing CRC errors or excessive drops',
 ARRAY[
   'Step 1: Check cable quality and length',
   'Step 2: Verify duplex settings match',
   'Step 3: Check for electromagnetic interference',
   'Step 4: Try different cable',
   'Step 5: Try different switch port',
   'Step 6: Clean fiber connectors if applicable',
   'Step 7: Consider replacing switch if multiple ports affected'
 ]),

('HIGH_TRAFFIC', 'medium',
 'Unusual traffic patterns detected',
 ARRAY[
   'Step 1: Analyze traffic type (broadcast, multicast)',
   'Step 2: Check for devices performing network scans',
   'Step 3: Verify no devices are flooding the network',
   'Step 4: Check switch CPU utilization',
   'Step 5: Monitor for MAC flooding attacks',
   'Step 6: Enable storm control on switch ports',
   'Step 7: Isolate problematic segment temporarily'
 ]),

-- Low severity / Info
('DEVICE_POWERED_OFF', 'low',
 'Device was previously active but is now powered off',
 ARRAY[
   'Step 1: Check if device was intentionally shut down',
   'Step 2: Verify power supply is connected',
   'Step 3: Check for scheduled maintenance',
   'Step 4: No action needed if planned downtime',
   'Step 5: If unexpected, investigate further'
 ]),

('NEW_DEVICE_DETECTED', 'info',
 'New device appeared on network',
 ARRAY[
   'Step 1: Verify device is authorized',
   'Step 2: Check device type and manufacturer',
   'Step 3: Update asset inventory if legitimate',
   'Step 4: Ensure device complies with security policies',
   'Step 5: Monitor for any unusual behavior'
 ]),

('DEVICE_REMOVED', 'info',
 'Device no longer appears on network',
 ARRAY[
   'Step 1: Check if device was legitimately removed',
   'Step 2: Update asset inventory',
   'Step 3: Verify no unauthorized removal',
   'Step 4: Monitor for device reappearance'
 ]);

-- Add indexes to existing tables
CREATE INDEX IF NOT EXISTS idx_firewall_interfaces_ip ON firewall_interfaces(ip_address);
CREATE INDEX IF NOT EXISTS idx_firewall_interfaces_subnet ON firewall_interfaces(subnet_cidr);
CREATE INDEX IF NOT EXISTS idx_managed_switches_ip ON managed_switches(switch_ip);

-- Add diagnostic tracking to network_setup
ALTER TABLE network_setup ADD COLUMN IF NOT EXISTS last_diagnostic_run TIMESTAMP;
ALTER TABLE network_setup ADD COLUMN IF NOT EXISTS diagnostic_status VARCHAR(20) DEFAULT 'never';

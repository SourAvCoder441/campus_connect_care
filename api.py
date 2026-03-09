from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / '.env')

app = Flask(__name__)
CORS(app)

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME', 'campusdb'),
        user=os.getenv('DB_USER', 'campusadmin'),
        password=os.getenv('DB_PASSWORD', 'campus123'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432')
    )

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Create users table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role VARCHAR(30) NOT NULL,
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create diagnostic_sessions if not exists
    cur.execute("""
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
            total_devices_found INTEGER DEFAULT 0,
            total_faults_detected INTEGER DEFAULT 0,
            critical_faults INTEGER DEFAULT 0,
            high_faults INTEGER DEFAULT 0,
            medium_faults INTEGER DEFAULT 0,
            low_faults INTEGER DEFAULT 0,
            info_faults INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create diagnostic_devices if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnostic_devices (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
            hostname VARCHAR(100),
            ip_address VARCHAR(45) NOT NULL,
            mac_address VARCHAR(17),
            subnet VARCHAR(45),
            switch_ip VARCHAR(45),
            switch_port VARCHAR(20),
            status VARCHAR(20) NOT NULL,
            confidence_score FLOAT DEFAULT 0.0,
            in_dhcp BOOLEAN DEFAULT FALSE,
            in_arp BOOLEAN DEFAULT FALSE,
            responds_to_ping BOOLEAN DEFAULT FALSE,
            in_mac_table BOOLEAN DEFAULT FALSE,
            device_type VARCHAR(50),
            manufacturer VARCHAR(100),
            response_time_ms FLOAT,
            first_seen TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create detected_faults if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detected_faults (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
            fault_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            primary_device_id INTEGER REFERENCES diagnostic_devices(id) ON DELETE CASCADE,
            secondary_device_id INTEGER REFERENCES diagnostic_devices(id),
            affected_ips TEXT[],
            affected_macs TEXT[],
            description TEXT NOT NULL,
            evidence JSONB,
            confidence FLOAT DEFAULT 1.0,
            troubleshooting_steps TEXT[] NOT NULL,
            is_resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMP,
            resolved_by INTEGER REFERENCES users(id),
            resolution_notes TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Insert sample users if empty
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO users (username, password_hash, role, email) VALUES
            ('netadmin', 'campus123', 'NetworkAdmin', 'netadmin@gec.edu'),
            ('secadmin', 'campus123', 'SecurityAdmin', 'secadmin@gec.edu')
        """)

    # Insert sample diagnostic session if empty
    cur.execute("SELECT COUNT(*) FROM diagnostic_sessions")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO diagnostic_sessions 
            (user_id, status, scan_type, target_subnet, summary,
             total_devices_found, total_faults_detected, 
             critical_faults, high_faults, medium_faults, low_faults,
             end_time)
            VALUES
            (1, 'completed', 'full', '192.168.10.0/24',
             'Full network scan completed. 2 critical faults detected.',
             7, 4, 2, 2, 0, 0, NOW()),
            (1, 'completed', 'full', '192.168.99.0/24',
             'Quick scan completed. 1 fault detected.',
             3, 1, 0, 1, 0, 0, NOW() - INTERVAL '2 hours')
        """)

        # Insert sample devices
        cur.execute("""
            INSERT INTO diagnostic_devices
            (session_id, hostname, ip_address, mac_address, subnet,
             switch_ip, switch_port, status, device_type,
             responds_to_ping, in_arp, response_time_ms)
            VALUES
            (1, 'Core-Switch', '192.168.10.1', 'AA:BB:CC:DD:EE:01',
             '192.168.10.0/24', NULL, NULL, 'active', 'switch',
             TRUE, TRUE, 1.2),
            (1, 'Camera-Block-A', '192.168.10.10', 'AA:BB:CC:DD:EE:02',
             '192.168.10.0/24', '192.168.10.1', 'Gi0/1', 'active', 'camera',
             TRUE, TRUE, 5.4),
            (1, 'Camera-Block-B', '192.168.10.11', 'AA:BB:CC:DD:EE:03',
             '192.168.10.0/24', '192.168.10.1', 'Gi0/2', 'unreachable', 'camera',
             FALSE, FALSE, NULL),
            (1, 'DVR-Main', '192.168.10.20', 'AA:BB:CC:DD:EE:04',
             '192.168.10.0/24', '192.168.10.1', 'Gi0/3', 'active', 'dvr',
             TRUE, TRUE, 3.1),
            (1, 'PC-Lab1', '192.168.10.30', 'AA:BB:CC:DD:EE:05',
             '192.168.10.0/24', '192.168.10.1', 'Gi0/4', 'active', 'pc',
             TRUE, TRUE, 2.8),
            (1, 'PC-Lab2', '192.168.10.31', 'AA:BB:CC:DD:EE:06',
             '192.168.10.0/24', '192.168.10.1', 'Gi0/5', 'active', 'pc',
             TRUE, TRUE, 2.9),
            (1, 'AP-Library', '192.168.10.50', 'AA:BB:CC:DD:EE:07',
             '192.168.10.0/24', '192.168.10.1', 'Gi0/6', 'active', 'ap',
             TRUE, TRUE, 1.8)
        """)

        # Insert sample faults
        cur.execute("""
            INSERT INTO detected_faults
            (session_id, fault_type, severity, primary_device_id,
             affected_ips, description, troubleshooting_steps,
             is_resolved, confidence)
            VALUES
            (1, 'DEVICE_UNREACHABLE', 'critical', 3,
             ARRAY['192.168.10.11'],
             'Camera-Block-B does not respond to ICMP ping. Device may be powered off or cable disconnected.',
             ARRAY[
               'Check if device is powered on (LED indicators)',
               'Verify network cable is connected securely',
               'Check switch port status - is it up/down?',
               'Verify VLAN configuration on switch port',
               'Check for IP address conflicts',
               'Try pinging from different source',
               'Replace cable if suspecting physical issue'
             ],
             FALSE, 0.95),

            (1, 'IP_CONFLICT', 'critical', 5,
             ARRAY['192.168.10.30', '192.168.10.30'],
             'IP conflict detected at 192.168.10.30. Multiple devices responding to same IP address.',
             ARRAY[
               'Identify all devices with conflicting IP (check ARP table)',
               'Check DHCP server logs for duplicate lease assignments',
               'Verify if any devices have static IPs in DHCP range',
               'Change IP of one conflicting device temporarily',
               'For static devices, assign unique IP outside DHCP range',
               'For DHCP devices, add MAC reservation',
               'Clear ARP cache on firewall after changes'
             ],
             FALSE, 0.99),

            (1, 'HIGH_LATENCY', 'high', 2,
             ARRAY['192.168.10.10'],
             'Camera-Block-A showing high latency (>100ms). May affect video streaming quality.',
             ARRAY[
               'Check for bandwidth saturation on links',
               'Verify no network loops causing congestion',
               'Check for faulty hardware (cables, ports)',
               'Monitor for unusual traffic patterns',
               'Check if latency is consistent or intermittent',
               'Verify QoS configurations if applicable',
               'Consider upgrading link capacity if persistent'
             ],
             FALSE, 0.87),

            (1, 'CABLE_FAILURE', 'high', 7,
             ARRAY['192.168.10.50'],
             'AP-Library showing intermittent connectivity. Possible cable fault on Gi0/6.',
             ARRAY[
               'Check physical connection at device side',
               'Check physical connection at switch side',
               'Verify link LEDs on both switch port and device NIC',
               'Try different cable if available',
               'Check switch port configuration',
               'Check for port errors using switch commands',
               'Try different switch port'
             ],
             TRUE, 0.82)
        """)

    conn.commit()
    cur.close()
    conn.close()

# OTP store
otp_store = {}

# ── AUTH ──────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT id, username, role FROM users WHERE username=%s AND password_hash=%s",
            (username, password)
        )
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            return jsonify({
                'success': True,
                'user': dict(user)
            })
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── DIAGNOSTIC SESSIONS ───────────────────────────
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                ds.id,
                ds.status,
                ds.scan_type,
                ds.target_subnet,
                ds.summary,
                ds.total_devices_found,
                ds.total_faults_detected,
                ds.critical_faults,
                ds.high_faults,
                ds.medium_faults,
                ds.low_faults,
                ds.info_faults,
                TO_CHAR(ds.start_time, 'DD Mon YYYY HH12:MI AM') as start_time,
                TO_CHAR(ds.end_time, 'HH12:MI AM') as end_time,
                u.username
            FROM diagnostic_sessions ds
            LEFT JOIN users u ON ds.user_id = u.id
            ORDER BY ds.start_time DESC
            LIMIT 20
        """)
        sessions = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── FAULTS ────────────────────────────────────────
@app.route('/api/faults', methods=['GET'])
def get_faults():
    session_id = request.args.get('session_id')
    resolved = request.args.get('resolved', 'false')

    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT 
                df.id,
                df.session_id,
                df.fault_type,
                df.severity,
                df.description,
                df.affected_ips,
                df.affected_macs,
                df.troubleshooting_steps,
                df.is_resolved,
                df.confidence,
                df.resolution_notes,
                TO_CHAR(df.detected_at, 'HH12:MI AM') as detected_at,
                TO_CHAR(df.resolved_at, 'DD Mon HH12:MI AM') as resolved_at,
                dd.hostname as device_name,
                dd.ip_address,
                dd.device_type,
                dd.switch_port
            FROM detected_faults df
            LEFT JOIN diagnostic_devices dd ON df.primary_device_id = dd.id
            WHERE 1=1
        """
        params = []

        if session_id:
            query += " AND df.session_id = %s"
            params.append(int(session_id))

        if resolved == 'false':
            query += " AND df.is_resolved = FALSE"
        elif resolved == 'true':
            query += " AND df.is_resolved = TRUE"

        query += " ORDER BY CASE df.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END, df.detected_at DESC"

        cur.execute(query, params)
        faults = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()

        return jsonify({'success': True, 'faults': faults})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── UPDATE FAULT STATUS ───────────────────────────
@app.route('/api/faults/<int:fault_id>/resolve', methods=['PUT'])
def resolve_fault(fault_id):
    data = request.json
    notes = data.get('notes', '')

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE detected_faults 
            SET is_resolved = TRUE,
                resolved_at = NOW(),
                resolution_notes = %s
            WHERE id = %s
        """, (notes, fault_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── DEVICES PER SESSION ───────────────────────────
@app.route('/api/sessions/<int:session_id>/devices', methods=['GET'])
def get_session_devices(session_id):
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("""
            SELECT 
                id, hostname, ip_address, mac_address,
                subnet, switch_ip, switch_port, status,
                device_type, manufacturer, response_time_ms,
                responds_to_ping, in_arp, in_dhcp, in_mac_table,
                confidence_score
            FROM diagnostic_devices
            WHERE session_id = %s
            ORDER BY status, ip_address
        """, (session_id,))
        devices = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'success': True, 'devices': devices})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── STATS ─────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        conn = get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Get latest session stats
        cur.execute("""
            SELECT 
                total_devices_found,
                total_faults_detected,
                critical_faults,
                high_faults,
                medium_faults,
                low_faults,
                target_subnet,
                TO_CHAR(start_time, 'DD Mon HH12:MI AM') as last_scan
            FROM diagnostic_sessions
            ORDER BY start_time DESC
            LIMIT 1
        """)
        stats = cur.fetchone()

        # Get unresolved faults count
        cur.execute("""
            SELECT COUNT(*) as unresolved 
            FROM detected_faults 
            WHERE is_resolved = FALSE
        """)
        unresolved = cur.fetchone()

        cur.close()
        conn.close()

        return jsonify({
            'success': True,
            'stats': dict(stats) if stats else {},
            'unresolved_faults': unresolved['unresolved'] if unresolved else 0
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ── FORGOT PASSWORD ───────────────────────────────
@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    username = data.get('username')

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT email FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not row[0]:
            return jsonify({'success': False, 'message': 'Username not found'}), 404

        email = row[0]
        otp = str(random.randint(100000, 999999))
        otp_store[username] = otp

        try:
            sender_email = "your_gmail@gmail.com"
            sender_password = "your_app_password"

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = 'Campus Connect Care - Password Reset OTP'

            body = f"""
Hello {username},
Your OTP for password reset is: {otp}
This OTP is valid for 10 minutes.
Campus Connect Care - GEC Idukki
            """
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
            server.quit()

            masked = email[:2] + '****' + email[email.index('@'):]
            return jsonify({
                'success': True,
                'message': f'OTP sent to {masked}'
            })
        except Exception:
            return jsonify({
                'success': True,
                'message': f'OTP (test mode): {otp}',
                'otp': otp
            })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    username = data.get('username')
    otp = data.get('otp')

    if otp_store.get(username) == otp:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Invalid OTP'}), 400

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    username = data.get('username')
    otp = data.get('otp')
    new_password = data.get('newPassword')

    if otp_store.get(username) != otp:
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash=%s WHERE username=%s",
            (new_password, username)
        )
        conn.commit()
        cur.close()
        conn.close()
        del otp_store[username]
        return jsonify({'success': True, 'message': 'Password reset successful'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    print("Initializing database tables...")
    try:
        init_db()
        print("Database ready!")
    except Exception as e:
        print(f"DB init failed: {e}")
        print("Starting API without DB init...")

    print("Starting Campus Connect Care API...")
    print("API running at http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
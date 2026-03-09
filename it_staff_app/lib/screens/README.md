# Campus Connect Care 🌐

A campus network monitoring and diagnostic tool for GEC Idukki.
Built with Python (Flask API) + Flutter (Android App) + PostgreSQL.

---

## 📱 Features

- Network Topology View with color-coded device status
- Problem tracking with step-by-step fix instructions
- Mark problems as Open / In Progress / Resolved
- Device status auto-updates when problems are resolved
- Forgot password with OTP
- Instagram-style clean UI

---

## 🏗️ Project Structure
```
campus_connect_care/
├── app/                  → Desktop Python app (PySide6)
├── it_staff_app/         → Flutter Android app
├── topology/             → SNMP/LLDP topology discovery
├── student_limit/        → Student portal
├── config/               → Settings
├── api.py                → Flask REST API
├── requirements.txt      → Python dependencies
└── README.md             → This file
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```cmd
git clone https://github.com/aadhicypher/campus_connect_care
cd campus_connect_care
```

### 2. Install Python Dependencies
```cmd
pip install flask flask-cors psycopg2-binary python-dotenv
```

### 3. Install PostgreSQL

- Download from: https://www.postgresql.org/download/windows/
- During installation:
  - Set password: `campus123`
  - Port: `5432` (default)
  - Click Next for everything else

### 4. Setup Database

Open CMD and run:
```cmd
psql -U postgres
```

Then paste these SQL commands:
```sql
CREATE DATABASE campusdb;
CREATE USER campusadmin WITH PASSWORD 'campus123';
GRANT ALL PRIVILEGES ON DATABASE campusdb TO campusadmin;
\q
```

Then:
```cmd
psql -U postgres -d campusdb
```
```sql
GRANT ALL ON SCHEMA public TO campusadmin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO campusadmin;
ALTER USER campusadmin CREATEDB;
```

Add default users:
```sql
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(30) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (username, password_hash, role, email) VALUES
('netadmin', 'campus123', 'NetworkAdmin', 'netadmin@gec.edu'),
('secadmin', 'campus123', 'SecurityAdmin', 'secadmin@gec.edu');
```
```sql
\q
```

### 5. Run the Flask API
```cmd
cd campus_connect_care
python api.py
```

You should see:
```
Database ready!
Running on http://0.0.0.0:5000
```

Note your PC IP address shown (e.g. `http://192.168.1.100:5000`)

### 6. Setup Flutter App

#### Install Flutter
- Download from: https://flutter.dev/docs/get-started/install
- Add Flutter to PATH

#### Update IP Address
Open this file:
```
it_staff_app/lib/screens/login_screen.dart
```

Find this line and change to your PC's IP:
```dart
const String baseUrl = 'http://YOUR_PC_IP:5000';
```

Find your IP by running `ipconfig` in CMD — look for **IPv4 Address**.

Also update the same IP in:
```
it_staff_app/lib/services/api_service.dart
it_staff_app/lib/screens/forgot_password_screen.dart
```

#### Run the App
```cmd
cd it_staff_app
flutter pub get
flutter run
```

---

## 🔐 Default Login Credentials

| Username | Password | Role |
|----------|----------|------|
| netadmin | campus123 | Network Admin |
| secadmin | campus123 | Security Admin |

---

## 🗄️ Useful Database Commands
```cmd
psql -U postgres -d campusdb
```
```sql
-- View all tables
\dt

-- View devices
SELECT * FROM devices;

-- View problems
SELECT * FROM problems;

-- View users
SELECT * FROM users;

-- Reset test data
UPDATE problems SET status='Open' WHERE id=1;
UPDATE problems SET status='In Progress' WHERE id=2;
UPDATE problems SET status='Open' WHERE id=3;
UPDATE problems SET status='Resolved' WHERE id=4;
UPDATE devices SET status='critical' WHERE id=3;
UPDATE devices SET status='critical' WHERE id=6;
UPDATE devices SET status='warning' WHERE id=2;
UPDATE devices SET status='warning' WHERE id=7;
UPDATE devices SET status='ok' WHERE id=1;
UPDATE devices SET status='ok' WHERE id=4;
UPDATE devices SET status='ok' WHERE id=5;

-- Exit
\q
```

---

## 🚀 Daily Development Workflow

### Start working:
```cmd
# Terminal 1 - Start API
cd campus_connect_care
python api.py

# Terminal 2 - Run Flutter app
cd campus_connect_care/it_staff_app
flutter run
```

### Save changes to GitHub:
```cmd
git add .
git commit -m "your message here"
git push origin main
```

---

## 👥 Team - Group 5

| Name | Roll No | GitHub Branch |
|------|---------|---------------|
| Adithyan Manoj | IDK22CS003 | main |
| Deion Tomson | IDK22CS021 | deion |
| Nivedhya K V | IDK22CS047 | - |
| Sourav Saitus | IDK22CS057 | - |

**Guide:** Dr. Reena Nair
**Department:** Computer Science and Engineering
**College:** Government Engineering College Idukki

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/login | Login with username/password |
| GET | /api/devices | Get all network devices |
| GET | /api/problems | Get all problems |
| PUT | /api/problems/:id/status | Update problem status |
| GET | /api/stats | Get device statistics |
| POST | /api/forgot-password | Send OTP to email |
| POST | /api/verify-otp | Verify OTP |
| POST | /api/reset-password | Reset password |
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

const String baseUrl = 'http://10.251.206.68:5000';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _usernameController = TextEditingController();
  final _otpController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  int _step = 1; // 1=username, 2=otp, 3=new password
  bool _isLoading = false;
  String _username = '';
  String _message = '';
  bool _obscurePassword = true;

  Future<void> _sendOTP() async {
    if (_usernameController.text.trim().isEmpty) {
      setState(() => _message = 'Please enter your username');
      return;
    }

    setState(() {
      _isLoading = true;
      _message = '';
    });

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/forgot-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': _usernameController.text.trim()}),
      );
      final data = jsonDecode(response.body);

      setState(() {
        _isLoading = false;
        if (data['success']) {
          _username = _usernameController.text.trim();
          _step = 2;
          _message = data['message'];
        } else {
          _message = data['message'] ?? 'Failed to send OTP';
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = 'Cannot connect to server';
      });
    }
  }

  Future<void> _verifyOTP() async {
    if (_otpController.text.trim().isEmpty) {
      setState(() => _message = 'Please enter the OTP');
      return;
    }

    setState(() {
      _isLoading = true;
      _message = '';
    });

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/verify-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': _username,
          'otp': _otpController.text.trim(),
        }),
      );
      final data = jsonDecode(response.body);

      setState(() {
        _isLoading = false;
        if (data['success']) {
          _step = 3;
          _message = '';
        } else {
          _message = data['message'] ?? 'Invalid OTP';
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = 'Cannot connect to server';
      });
    }
  }

  Future<void> _resetPassword() async {
    if (_newPasswordController.text.isEmpty) {
      setState(() => _message = 'Please enter new password');
      return;
    }
    if (_newPasswordController.text != _confirmPasswordController.text) {
      setState(() => _message = 'Passwords do not match');
      return;
    }

    setState(() {
      _isLoading = true;
      _message = '';
    });

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/reset-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': _username,
          'otp': _otpController.text.trim(),
          'newPassword': _newPasswordController.text,
        }),
      );
      final data = jsonDecode(response.body);

      setState(() {
        _isLoading = false;
        if (data['success']) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Password reset successful! Please login.'),
              backgroundColor: Color(0xFF00C853),
              behavior: SnackBarBehavior.floating,
            ),
          );
          Navigator.pop(context);
        } else {
          _message = data['message'] ?? 'Failed to reset password';
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = 'Cannot connect to server';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0E1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A237E),
        title: const Text('Forgot Password',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              children: [
                // Step indicator
                Row(
                  children: [
                    _stepCircle(1, 'Username'),
                    _stepLine(),
                    _stepCircle(2, 'OTP'),
                    _stepLine(),
                    _stepCircle(3, 'Password'),
                  ],
                ),
                const SizedBox(height: 40),

                // Step content
                if (_step == 1) _buildStep1(),
                if (_step == 2) _buildStep2(),
                if (_step == 3) _buildStep3(),

                // Message
                if (_message.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: _message.contains('sent') || _message.contains('OTP')
                          ? const Color(0xFF00C853).withOpacity(0.15)
                          : const Color(0xFFFF1744).withOpacity(0.15),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: _message.contains('sent') || _message.contains('OTP')
                            ? const Color(0xFF00C853).withOpacity(0.4)
                            : const Color(0xFFFF1744).withOpacity(0.4),
                      ),
                    ),
                    child: Text(
                      _message,
                      style: TextStyle(
                        color: _message.contains('sent') || _message.contains('OTP')
                            ? const Color(0xFF00C853)
                            : const Color(0xFFFF1744),
                        fontSize: 13,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStep1() {
    return Column(
      children: [
        const Icon(Icons.lock_reset, color: Color(0xFF1A237E), size: 60),
        const SizedBox(height: 16),
        const Text('Enter your username',
            style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text('We will send an OTP to your registered email',
            style: TextStyle(color: Colors.white54, fontSize: 13),
            textAlign: TextAlign.center),
        const SizedBox(height: 24),
        TextField(
          controller: _usernameController,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'Username',
            labelStyle: const TextStyle(color: Colors.white54),
            prefixIcon: const Icon(Icons.person, color: Colors.white54),
            filled: true,
            fillColor: const Color(0xFF1C2333),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _sendOTP,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A237E),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(color: Colors.white)
                : const Text('Send OTP',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold)),
          ),
        ),
      ],
    );
  }

  Widget _buildStep2() {
    return Column(
      children: [
        const Icon(Icons.mark_email_read, color: Color(0xFF1A237E), size: 60),
        const SizedBox(height: 16),
        const Text('Enter OTP',
            style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        const Text('Check your email for the OTP',
            style: TextStyle(color: Colors.white54, fontSize: 13)),
        const SizedBox(height: 24),
        TextField(
          controller: _otpController,
          keyboardType: TextInputType.number,
          style: const TextStyle(
              color: Colors.white, fontSize: 24, letterSpacing: 8),
          textAlign: TextAlign.center,
          maxLength: 6,
          decoration: InputDecoration(
            labelText: 'Enter 6-digit OTP',
            labelStyle: const TextStyle(color: Colors.white54),
            counterStyle: const TextStyle(color: Colors.white38),
            filled: true,
            fillColor: const Color(0xFF1C2333),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _verifyOTP,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A237E),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(color: Colors.white)
                : const Text('Verify OTP',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold)),
          ),
        ),
        const SizedBox(height: 12),
        TextButton(
          onPressed: _sendOTP,
          child: const Text('Resend OTP',
              style: TextStyle(color: Colors.white54)),
        ),
      ],
    );
  }

  Widget _buildStep3() {
    return Column(
      children: [
        const Icon(Icons.lock_open, color: Color(0xFF00C853), size: 60),
        const SizedBox(height: 16),
        const Text('Set New Password',
            style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold)),
        const SizedBox(height: 24),
        TextField(
          controller: _newPasswordController,
          obscureText: _obscurePassword,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'New Password',
            labelStyle: const TextStyle(color: Colors.white54),
            prefixIcon: const Icon(Icons.lock, color: Colors.white54),
            suffixIcon: IconButton(
              icon: Icon(
                  _obscurePassword ? Icons.visibility : Icons.visibility_off,
                  color: Colors.white54),
              onPressed: () =>
                  setState(() => _obscurePassword = !_obscurePassword),
            ),
            filled: true,
            fillColor: const Color(0xFF1C2333),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _confirmPasswordController,
          obscureText: _obscurePassword,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: 'Confirm Password',
            labelStyle: const TextStyle(color: Colors.white54),
            prefixIcon: const Icon(Icons.lock_outline, color: Colors.white54),
            filled: true,
            fillColor: const Color(0xFF1C2333),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide.none,
            ),
          ),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _resetPassword,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00C853),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(color: Colors.white)
                : const Text('Reset Password',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold)),
          ),
        ),
      ],
    );
  }

  Widget _stepCircle(int step, String label) {
    final isActive = _step >= step;
    return Column(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: isActive ? const Color(0xFF1A237E) : const Color(0xFF1C2333),
            shape: BoxShape.circle,
            border: Border.all(
              color: isActive ? const Color(0xFF1A237E) : Colors.white24,
            ),
          ),
          child: Center(
            child: Text('$step',
                style: TextStyle(
                    color: isActive ? Colors.white : Colors.white38,
                    fontWeight: FontWeight.bold)),
          ),
        ),
        const SizedBox(height: 4),
        Text(label,
            style: TextStyle(
                color: isActive ? Colors.white : Colors.white38,
                fontSize: 11)),
      ],
    );
  }

  Widget _stepLine() {
    return Expanded(
      child: Container(
        height: 2,
        margin: const EdgeInsets.only(bottom: 20),
        color: Colors.white24,
      ),
    );
  }
}
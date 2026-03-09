import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

const String fpBaseUrl = 'http://10.103.169.68:5000';

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

  int _step = 1;
  bool _isLoading = false;
  String _username = '';
  String _message = '';
  bool _isSuccess = false;
  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  Future<void> _sendOTP() async {
    if (_usernameController.text.trim().isEmpty) {
      setState(() {
        _message = 'Please enter your username';
        _isSuccess = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _message = '';
    });

    try {
      final response = await http.post(
        Uri.parse('$fpBaseUrl/api/forgot-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(
            {'username': _usernameController.text.trim()}),
      );
      final data = jsonDecode(response.body);
      setState(() {
        _isLoading = false;
        if (data['success']) {
          _username = _usernameController.text.trim();
          _step = 2;
          _message = data['message'];
          _isSuccess = true;
        } else {
          _message = data['message'] ?? 'Failed to send OTP';
          _isSuccess = false;
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = 'Cannot connect to server';
        _isSuccess = false;
      });
    }
  }

  Future<void> _verifyOTP() async {
    if (_otpController.text.trim().isEmpty) {
      setState(() {
        _message = 'Please enter the OTP';
        _isSuccess = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _message = '';
    });

    try {
      final response = await http.post(
        Uri.parse('$fpBaseUrl/api/verify-otp'),
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
          _isSuccess = false;
        }
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = 'Cannot connect to server';
        _isSuccess = false;
      });
    }
  }

  Future<void> _resetPassword() async {
    if (_newPasswordController.text.isEmpty) {
      setState(() {
        _message = 'Please enter new password';
        _isSuccess = false;
      });
      return;
    }
    if (_newPasswordController.text != _confirmPasswordController.text) {
      setState(() {
        _message = 'Passwords do not match';
        _isSuccess = false;
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _message = '';
    });

    try {
      final response = await http.post(
        Uri.parse('$fpBaseUrl/api/reset-password'),
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
      });
      if (data['success']) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Password reset successful! Please login.'),
            backgroundColor: const Color(0xFF00C853),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10)),
          ),
        );
        Navigator.pop(context);
      } else {
        setState(() {
          _message = data['message'] ?? 'Failed to reset password';
          _isSuccess = false;
        });
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _message = 'Cannot connect to server';
        _isSuccess = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          'Reset Password',
          style: TextStyle(
            color: Color(0xFF262626),
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
        iconTheme: const IconThemeData(color: Color(0xFF262626)),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(color: Colors.grey.shade200, height: 1),
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const SizedBox(height: 20),

              // Step indicator
              Row(
                children: [
                  _stepCircle(1, 'Username'),
                  _stepLine(isActive: _step >= 2),
                  _stepCircle(2, 'OTP'),
                  _stepLine(isActive: _step >= 3),
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
                    color: _isSuccess
                        ? const Color(0xFF00C853).withOpacity(0.08)
                        : const Color(0xFFE53935).withOpacity(0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: _isSuccess
                          ? const Color(0xFF00C853).withOpacity(0.3)
                          : const Color(0xFFE53935).withOpacity(0.3),
                    ),
                  ),
                  child: Text(
                    _message,
                    style: TextStyle(
                      color: _isSuccess
                          ? const Color(0xFF00C853)
                          : const Color(0xFFE53935),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStep1() {
    return Column(
      children: [
        // Icon with gradient
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF833AB4), Color(0xFFE1306C)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFE1306C).withOpacity(0.3),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: const Icon(Icons.lock_reset_rounded,
              color: Colors.white, size: 38),
        ),
        const SizedBox(height: 20),
        const Text(
          'Forgot Password?',
          style: TextStyle(
            color: Color(0xFF262626),
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Enter your username to receive an OTP\non your registered email',
          style: TextStyle(
            color: Color(0xFF8E8E8E),
            fontSize: 13,
            height: 1.5,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        _inputField(
          controller: _usernameController,
          hint: 'Username',
          icon: Icons.person_outline,
        ),
        const SizedBox(height: 16),
        _gradientButton(
          label: 'Send OTP',
          onTap: _isLoading ? null : _sendOTP,
          isLoading: _isLoading,
        ),
      ],
    );
  }

  Widget _buildStep2() {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF833AB4), Color(0xFFE1306C)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFE1306C).withOpacity(0.3),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: const Icon(Icons.mark_email_read_rounded,
              color: Colors.white, size: 38),
        ),
        const SizedBox(height: 20),
        const Text(
          'Enter OTP',
          style: TextStyle(
            color: Color(0xFF262626),
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Check your email for the 6-digit OTP',
          style: TextStyle(color: Color(0xFF8E8E8E), fontSize: 13),
        ),
        const SizedBox(height: 32),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFFFAFAFA),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFDBDBDB)),
          ),
          child: TextField(
            controller: _otpController,
            keyboardType: TextInputType.number,
            textAlign: TextAlign.center,
            maxLength: 6,
            style: const TextStyle(
              color: Color(0xFF262626),
              fontSize: 28,
              fontWeight: FontWeight.bold,
              letterSpacing: 12,
            ),
            decoration: const InputDecoration(
              hintText: '------',
              hintStyle: TextStyle(
                color: Color(0xFFDBDBDB),
                fontSize: 28,
                letterSpacing: 12,
              ),
              border: InputBorder.none,
              counterText: '',
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            ),
          ),
        ),
        const SizedBox(height: 16),
        _gradientButton(
          label: 'Verify OTP',
          onTap: _isLoading ? null : _verifyOTP,
          isLoading: _isLoading,
        ),
        const SizedBox(height: 12),
        GestureDetector(
          onTap: _sendOTP,
          child: const Text(
            'Resend OTP',
            style: TextStyle(
              color: Color(0xFF0095F6),
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildStep3() {
    return Column(
      children: [
        Container(
          width: 80,
          height: 80,
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFF00C853), Color(0xFF00897B)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(24),
            boxShadow: [
              BoxShadow(
                color: const Color(0xFF00C853).withOpacity(0.3),
                blurRadius: 16,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: const Icon(Icons.lock_open_rounded,
              color: Colors.white, size: 38),
        ),
        const SizedBox(height: 20),
        const Text(
          'Set New Password',
          style: TextStyle(
            color: Color(0xFF262626),
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Choose a strong new password',
          style: TextStyle(color: Color(0xFF8E8E8E), fontSize: 13),
        ),
        const SizedBox(height: 32),
        _inputField(
          controller: _newPasswordController,
          hint: 'New Password',
          icon: Icons.lock_outline,
          isPassword: true,
          obscure: _obscurePassword,
          onToggle: () =>
              setState(() => _obscurePassword = !_obscurePassword),
        ),
        const SizedBox(height: 12),
        _inputField(
          controller: _confirmPasswordController,
          hint: 'Confirm Password',
          icon: Icons.lock_outline,
          isPassword: true,
          obscure: _obscureConfirm,
          onToggle: () =>
              setState(() => _obscureConfirm = !_obscureConfirm),
        ),
        const SizedBox(height: 16),
        _gradientButton(
          label: 'Reset Password',
          onTap: _isLoading ? null : _resetPassword,
          isLoading: _isLoading,
          colors: [const Color(0xFF00C853), const Color(0xFF00897B)],
        ),
      ],
    );
  }

  Widget _inputField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    bool isPassword = false,
    bool obscure = false,
    VoidCallback? onToggle,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFFAFAFA),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFDBDBDB)),
      ),
      child: TextField(
        controller: controller,
        obscureText: isPassword ? obscure : false,
        style:
            const TextStyle(color: Color(0xFF262626), fontSize: 14),
        decoration: InputDecoration(
          hintText: hint,
          hintStyle: const TextStyle(color: Color(0xFF8E8E8E)),
          prefixIcon:
              Icon(icon, color: const Color(0xFF8E8E8E), size: 20),
          suffixIcon: isPassword
              ? IconButton(
                  icon: Icon(
                    obscure
                        ? Icons.visibility_outlined
                        : Icons.visibility_off_outlined,
                    color: const Color(0xFF8E8E8E),
                    size: 20,
                  ),
                  onPressed: onToggle,
                )
              : null,
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
              horizontal: 16, vertical: 14),
        ),
      ),
    );
  }

  Widget _gradientButton({
    required String label,
    required VoidCallback? onTap,
    bool isLoading = false,
    List<Color> colors = const [Color(0xFF833AB4), Color(0xFFE1306C)],
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        height: 50,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: colors),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: colors[0].withOpacity(0.3),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Center(
          child: isLoading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  ),
                )
              : Text(
                  label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
        ),
      ),
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
            gradient: isActive
                ? const LinearGradient(
                    colors: [Color(0xFF833AB4), Color(0xFFE1306C)],
                  )
                : null,
            color: isActive ? null : const Color(0xFFF5F5F5),
            shape: BoxShape.circle,
          ),
          child: Center(
            child: Text(
              '$step',
              style: TextStyle(
                color: isActive ? Colors.white : const Color(0xFFB0B0B0),
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            color: isActive
                ? const Color(0xFF262626)
                : const Color(0xFFB0B0B0),
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _stepLine({required bool isActive}) {
    return Expanded(
      child: Container(
        height: 2,
        margin: const EdgeInsets.only(bottom: 20, left: 4, right: 4),
        decoration: BoxDecoration(
          gradient: isActive
              ? const LinearGradient(
                  colors: [Color(0xFF833AB4), Color(0xFFE1306C)],
                )
              : null,
          color: isActive ? null : const Color(0xFFF0F0F0),
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }
} 
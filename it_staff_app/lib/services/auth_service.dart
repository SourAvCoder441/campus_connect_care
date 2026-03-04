import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

const String baseUrl = 'http://10.251.206.68:5000';

class AuthService extends ChangeNotifier {
  bool _isLoggedIn = false;
  String _username = '';

  bool get isLoggedIn => _isLoggedIn;
  String get username => _username;

  Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );
      final data = jsonDecode(response.body);
      if (data['success']) {
        _isLoggedIn = true;
        _username = username;
        notifyListeners();
      }
      return data;
    } catch (e) {
      return {'success': false, 'message': 'Cannot connect to server'};
    }
  }

  void logout() {
    _isLoggedIn = false;
    _username = '';
    notifyListeners();
  }
}
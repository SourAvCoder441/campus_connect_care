import 'package:http/http.dart' as http;
import 'dart:convert';

const String baseUrl = 'http://10.251.206.68:5000';

class ApiService {
  static Future<List<Map<String, dynamic>>> getDevices() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/devices'));
      final data = jsonDecode(response.body);
      if (data['success']) {
        return List<Map<String, dynamic>>.from(data['devices']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  static Future<List<Map<String, dynamic>>> getProblems() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/api/problems'));
      final data = jsonDecode(response.body);
      if (data['success']) {
        return List<Map<String, dynamic>>.from(data['problems']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  static Future<bool> updateProblemStatus(String id, String status) async {
    try {
      final response = await http.put(
        Uri.parse('$baseUrl/api/problems/$id/status'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'status': status}),
      );
      final data = jsonDecode(response.body);
      return data['success'];
    } catch (e) {
      return false;
    }
  }
}
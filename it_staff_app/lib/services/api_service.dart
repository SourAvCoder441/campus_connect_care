import 'package:http/http.dart' as http;
import 'dart:convert';

const String baseUrl = 'http://10.103.169.68:5000';

class ApiService {
  // ── SESSIONS ─────────────────────────────────────
  static Future<List<Map<String, dynamic>>> getSessions() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/api/sessions'))
          .timeout(const Duration(seconds: 10));
      final data = jsonDecode(response.body);
      if (data['success']) {
        return List<Map<String, dynamic>>.from(data['sessions']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  // ── FAULTS ───────────────────────────────────────
  static Future<List<Map<String, dynamic>>> getFaults({
    String? sessionId,
    String resolved = 'all',
  }) async {
    try {
      String url = '$baseUrl/api/faults?resolved=$resolved';
      if (sessionId != null) url += '&session_id=$sessionId';
      final response = await http
          .get(Uri.parse(url))
          .timeout(const Duration(seconds: 10));
      final data = jsonDecode(response.body);
      if (data['success']) {
        return List<Map<String, dynamic>>.from(data['faults']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  // ── UPDATE FAULT STATUS ───────────────────────────
  static Future<bool> updateFaultStatus(String faultId, String status,
      {String notes = ''}) async {
    try {
      final response = await http
          .put(
            Uri.parse('$baseUrl/api/faults/$faultId/status'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'status': status, 'notes': notes}),
          )
          .timeout(const Duration(seconds: 10));
      final data = jsonDecode(response.body);
      return data['success'];
    } catch (e) {
      return false;
    }
  }

  // ── RESOLVE FAULT (compatibility) ─────────────────
  static Future<bool> resolveFault(String faultId,
      {String notes = ''}) async {
    return updateFaultStatus(faultId, 'Resolved', notes: notes);
  }

  // ── SESSION DEVICES ───────────────────────────────
  static Future<List<Map<String, dynamic>>> getSessionDevices(
      String sessionId) async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/api/sessions/$sessionId/devices'))
          .timeout(const Duration(seconds: 10));
      final data = jsonDecode(response.body);
      if (data['success']) {
        return List<Map<String, dynamic>>.from(data['devices']);
      }
      return [];
    } catch (e) {
      return [];
    }
  }

  // ── STATS ─────────────────────────────────────────
  static Future<Map<String, dynamic>> getStats() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/api/stats'))
          .timeout(const Duration(seconds: 10));
      final data = jsonDecode(response.body);
      if (data['success']) return data;
      return {};
    } catch (e) {
      return {};
    }
  }

  // ── OLD COMPATIBILITY ─────────────────────────────
  static Future<List<Map<String, dynamic>>> getProblems() async {
    return getFaults();
  }

  static Future<bool> updateProblemStatus(
      String id, String status) async {
    if (status == 'Resolved') return resolveFault(id);
    return updateFaultStatus(id, status);
  }
}
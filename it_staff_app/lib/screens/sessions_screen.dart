import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'faults_screen.dart';
import 'session_devices_screen.dart';

class SessionsScreen extends StatefulWidget {
  const SessionsScreen({super.key});

  @override
  State<SessionsScreen> createState() => _SessionsScreenState();
}

class _SessionsScreenState extends State<SessionsScreen> {
  List<Map<String, dynamic>> sessions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadSessions();
  }

  Future<void> _loadSessions() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getSessions();
    setState(() {
      sessions = data;
      _isLoading = false;
    });
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'completed':
        return const Color(0xFF00C853);
      case 'running':
        return const Color(0xFF1E88E5);
      case 'failed':
        return const Color(0xFFE53935);
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          'Diagnostic Sessions',
          style: TextStyle(
            color: Color(0xFF262626),
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF262626)),
            onPressed: _loadSessions,
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Divider(color: Colors.grey.shade200, height: 1),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(
                    Color(0xFFE1306C)),
              ),
            )
          : RefreshIndicator(
              onRefresh: _loadSessions,
              color: const Color(0xFFE1306C),
              child: sessions.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.history,
                              size: 60,
                              color: Colors.grey.shade300),
                          const SizedBox(height: 12),
                          const Text(
                            'No diagnostic sessions yet',
                            style: TextStyle(
                              color: Color(0xFF8E8E8E),
                              fontSize: 16,
                            ),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: sessions.length,
                      itemBuilder: (context, index) {
                        return _sessionCard(sessions[index]);
                      },
                    ),
            ),
    );
  }

  Widget _sessionCard(Map<String, dynamic> session) {
    final statusColor = _statusColor(session['status'] ?? '');
    final criticalCount = session['critical_faults'] ?? 0;
    final highCount = session['high_faults'] ?? 0;

    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => FaultsScreen(
              sessionId: session['id'].toString(),
              sessionName: session['start_time'] ?? '',
            ),
          ),
        );
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 12,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          children: [
            // Top color bar
            Container(
              height: 4,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF833AB4), Color(0xFFE1306C)],
                ),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(16),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: const Color(0xFF833AB4).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Icon(Icons.radar,
                            color: Color(0xFF833AB4), size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              session['start_time'] ?? '',
                              style: const TextStyle(
                                color: Color(0xFF262626),
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                            Text(
                              'Subnet: ${session['target_subnet'] ?? 'N/A'}',
                              style: const TextStyle(
                                color: Color(0xFF8E8E8E),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          (session['status'] ?? '').toUpperCase(),
                          style: TextStyle(
                            color: statusColor,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (session['summary'] != null)
                    Text(
                      session['summary'],
                      style: const TextStyle(
                        color: Color(0xFF8E8E8E),
                        fontSize: 12,
                        height: 1.4,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  const SizedBox(height: 12),
                  Divider(color: Colors.grey.shade100, height: 1),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      _miniStat(
                        Icons.devices_outlined,
                        '${session['total_devices_found'] ?? 0} devices',
                        const Color(0xFF1E88E5),
                      ),
                      const SizedBox(width: 12),
                      if (criticalCount > 0)
                        _miniStat(
                          Icons.error_outline,
                          '$criticalCount critical',
                          const Color(0xFFE53935),
                        ),
                      if (criticalCount > 0) const SizedBox(width: 12),
                      if (highCount > 0)
                        _miniStat(
                          Icons.warning_amber_outlined,
                          '$highCount high',
                          const Color(0xFFFFB300),
                        ),
                      const Spacer(),
                      Row(
                        children: [
                          const Icon(Icons.chevron_right,
                              color: Color(0xFF8E8E8E), size: 18),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  // View devices button
                  GestureDetector(
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => SessionDevicesScreen(
                            sessionId: session['id'].toString(),
                            sessionName: session['start_time'] ?? '',
                          ),
                        ),
                      );
                    },
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFAFAFA),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                            color: Colors.grey.shade200),
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.devices,
                              size: 14, color: Color(0xFF8E8E8E)),
                          SizedBox(width: 6),
                          Text(
                            'View Discovered Devices',
                            style: TextStyle(
                              color: Color(0xFF8E8E8E),
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _miniStat(IconData icon, String label, Color color) {
    return Row(
      children: [
        Icon(icon, size: 13, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
import 'package:flutter/material.dart';
import 'sessions_screen.dart';
import 'faults_screen.dart';
import '../services/api_service.dart';
import 'session_devices_screen.dart';

class TopologyScreen extends StatefulWidget {
  const TopologyScreen({super.key});

  @override
  State<TopologyScreen> createState() => _TopologyScreenState();
}

class _TopologyScreenState extends State<TopologyScreen> {
  Map<String, dynamic> stats = {};
  List<Map<String, dynamic>> faults = [];
  bool _isLoading = true;
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final statsData = await ApiService.getStats();
    final faultsData = await ApiService.getFaults();
    setState(() {
      stats = statsData;
      faults = faultsData;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      body: IndexedStack(
        index: _selectedIndex,
        children: const [
          _DashboardTab(),
          SessionsScreen(),
          FaultsScreen(),
        ],
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 12,
              offset: const Offset(0, -2),
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _selectedIndex,
          onTap: (i) => setState(() => _selectedIndex = i),
          backgroundColor: Colors.white,
          selectedItemColor: const Color(0xFFE1306C),
          unselectedItemColor: const Color(0xFF8E8E8E),
          elevation: 0,
          type: BottomNavigationBarType.fixed,
          selectedLabelStyle: const TextStyle(
              fontWeight: FontWeight.w600, fontSize: 11),
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_outlined),
              activeIcon: Icon(Icons.dashboard),
              label: 'Dashboard',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.history_outlined),
              activeIcon: Icon(Icons.history),
              label: 'Sessions',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.warning_amber_outlined),
              activeIcon: Icon(Icons.warning_amber),
              label: 'Faults',
            ),
          ],
        ),
      ),
    );
  }
}

class _DashboardTab extends StatefulWidget {
  const _DashboardTab();

  @override
  State<_DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<_DashboardTab> {
  Map<String, dynamic> stats = {};
  List<Map<String, dynamic>> recentFaults = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final statsData = await ApiService.getStats();
    final faultsData = await ApiService.getFaults();
    setState(() {
      stats = statsData;
      recentFaults = faultsData.take(3).toList();
      _isLoading = false;
    });
  }

  Color _severityColor(String severity) {
    switch (severity) {
      case 'critical':
        return const Color(0xFFE53935);
      case 'high':
        return const Color(0xFFFFB300);
      case 'medium':
        return const Color(0xFF1E88E5);
      case 'low':
        return const Color(0xFF00C853);
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = stats['stats'] ?? {};
    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          'Campus Connect Care',
          style: TextStyle(
            color: Color(0xFF262626),
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF262626)),
            onPressed: _loadData,
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
              onRefresh: _loadData,
              color: const Color(0xFFE1306C),
              child: SingleChildScrollView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Last scan info
                    if (s['last_scan'] != null)
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [
                              Color(0xFF833AB4),
                              Color(0xFFE1306C),
                            ],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(16),
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFFE1306C)
                                  .withOpacity(0.3),
                              blurRadius: 16,
                              offset: const Offset(0, 6),
                            ),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.radar,
                                    color: Colors.white, size: 18),
                                SizedBox(width: 8),
                                Text(
                                  'Last Diagnostic Scan',
                                  style: TextStyle(
                                    color: Colors.white70,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              s['last_scan'] ?? '',
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Subnet: ${s['target_subnet'] ?? 'N/A'}',
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    const SizedBox(height: 16),

                    // Stats grid
                    // Stats grid
                    const Text(
                      'Scan Summary',
                      style: TextStyle(
                        color: Color(0xFF262626),
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _statCard(
                          'Devices Found',
                          '${s['total_devices_found'] ?? 0}',
                          Icons.devices_outlined,
                          const Color(0xFF1E88E5),
                          onTap: () {
                            // Get latest session id from stats
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => SessionDevicesScreen(
                                  sessionId: '1',
                                  sessionName: s['last_scan'] ?? '',
                                ),
                              ),
                            );
                          },
                        ),
                        const SizedBox(width: 12),
                        _statCard(
                          'Total Faults',
                          '${s['total_faults_detected'] ?? 0}',
                          Icons.bug_report_outlined,
                          const Color(0xFFE53935),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const FaultsScreen(),
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _statCard(
                          'Critical',
                          '${s['critical_faults'] ?? 0}',
                          Icons.error_outline,
                          const Color(0xFFE53935),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const FaultsScreen(
                                  initialFilter: 'Critical',
                                ),
                              ),
                            );
                          },
                        ),
                        const SizedBox(width: 12),
                        _statCard(
                          'High',
                          '${s['high_faults'] ?? 0}',
                          Icons.warning_amber_outlined,
                          const Color(0xFFFFB300),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const FaultsScreen(
                                  initialFilter: 'High',
                                ),
                              ),
                            );
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        _statCard(
                          'Unresolved',
                          '${stats['unresolved_faults'] ?? 0}',
                          Icons.pending_outlined,
                          const Color(0xFF8E8E8E),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const FaultsScreen(),
                              ),
                            );
                          },
                        ),
                        const SizedBox(width: 12),
                        _statCard(
                          'Medium/Low',
                          '${(s['medium_faults'] ?? 0) + (s['low_faults'] ?? 0)}',
                          Icons.info_outline,
                          const Color(0xFF00C853),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => const FaultsScreen(
                                  initialFilter: 'Medium',
                                ),
                              ),
                            );
                          },
                        ),
                      ],
                    ),

                    // Recent faults
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Recent Faults',
                          style: TextStyle(
                            color: Color(0xFF262626),
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        GestureDetector(
                          onTap: () {},
                          child: const Text(
                            'See all',
                            style: TextStyle(
                              color: Color(0xFF0095F6),
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (recentFaults.isEmpty)
                      Center(
                        child: Column(
                          children: [
                            Icon(Icons.check_circle_outline,
                                size: 48,
                                color: Colors.grey.shade300),
                            const SizedBox(height: 8),
                            const Text(
                              'No active faults!',
                              style: TextStyle(
                                  color: Color(0xFF8E8E8E),
                                  fontSize: 14),
                            ),
                          ],
                        ),
                      )
                    else
                      ...recentFaults.map((fault) {
                        final color =
                            _severityColor(fault['severity'] ?? '');
                        return Container(
                          margin: const EdgeInsets.only(bottom: 10),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.04),
                                blurRadius: 8,
                                offset: const Offset(0, 2),
                              ),
                            ],
                          ),
                          child: Row(
                            children: [
                              Container(
                                width: 40,
                                height: 40,
                                decoration: BoxDecoration(
                                  color: color.withOpacity(0.1),
                                  borderRadius:
                                      BorderRadius.circular(12),
                                ),
                                child: Icon(
                                  Icons.warning_amber_rounded,
                                  color: color,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment:
                                      CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      fault['fault_type']
                                              ?.replaceAll('_', ' ') ??
                                          '',
                                      style: const TextStyle(
                                        color: Color(0xFF262626),
                                        fontWeight: FontWeight.w600,
                                        fontSize: 13,
                                      ),
                                    ),
                                    Text(
                                      fault['device_name'] ??
                                          fault['ip_address'] ??
                                          '',
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
                                    horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: color.withOpacity(0.1),
                                  borderRadius:
                                      BorderRadius.circular(20),
                                ),
                                child: Text(
                                  fault['severity']?.toUpperCase() ??
                                      '',
                                  style: TextStyle(
                                    color: color,
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _statCard(
      String label, String value, IconData icon, Color color,
      {VoidCallback? onTap}) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(16),
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
            border: onTap != null
                ? Border.all(color: color.withOpacity(0.15))
                : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Icon(icon, color: color, size: 20),
                  ),
                  if (onTap != null)
                    Icon(Icons.arrow_forward_ios,
                        size: 12, color: Colors.grey.shade400),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                value,
                style: TextStyle(
                  color: color,
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: const TextStyle(
                  color: Color(0xFF8E8E8E),
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
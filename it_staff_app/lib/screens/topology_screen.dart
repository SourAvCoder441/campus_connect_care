import 'package:flutter/material.dart';
import 'problems_screen.dart';
import '../services/api_service.dart';

class TopologyScreen extends StatefulWidget {
  const TopologyScreen({super.key});

  @override
  State<TopologyScreen> createState() => _TopologyScreenState();
}

class _TopologyScreenState extends State<TopologyScreen> {
  List<Map<String, dynamic>> devices = [];
  bool _isLoading = true;
  String _selectedFilter = 'All';
  final List<String> _filters = ['All', 'Critical', 'Warning', 'OK'];

  @override
  void initState() {
    super.initState();
    _loadDevices();
  }

  Future<void> _loadDevices() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getDevices();
    setState(() {
      devices = data;
      _isLoading = false;
    });
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'ok':
        return const Color(0xFF00C853);
      case 'warning':
        return const Color(0xFFFFD600);
      case 'critical':
        return const Color(0xFFFF1744);
      default:
        return Colors.grey;
    }
  }

  IconData _deviceIcon(String type) {
    switch (type) {
      case 'switch':
        return Icons.device_hub;
      case 'camera':
        return Icons.videocam;
      case 'dvr':
        return Icons.video_settings;
      default:
        return Icons.devices;
    }
  }

  List<Map<String, dynamic>> get _filteredDevices {
    if (_selectedFilter == 'All') return devices;
    return devices
        .where((d) => d['status'] == _selectedFilter.toLowerCase())
        .toList();
  }

  int get _criticalCount =>
      devices.where((d) => d['status'] == 'critical').length;
  int get _warningCount =>
      devices.where((d) => d['status'] == 'warning').length;
  int get _okCount => devices.where((d) => d['status'] == 'ok').length;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0E1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A237E),
        title: const Text(
          'Network Topology',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.warning_amber, color: Colors.white),
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ProblemsScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _loadDevices,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Colors.white))
          : Column(
              children: [
                // Status summary bar
                Container(
                  padding: const EdgeInsets.all(16),
                  color: const Color(0xFF1C2333),
                  child: Row(
                    children: [
                      _statusTile('Critical', _criticalCount,
                          const Color(0xFFFF1744)),
                      const SizedBox(width: 12),
                      _statusTile('Warning', _warningCount,
                          const Color(0xFFFFD600)),
                      const SizedBox(width: 12),
                      _statusTile('OK', _okCount, const Color(0xFF00C853)),
                    ],
                  ),
                ),

                // Filter chips
                Container(
                  height: 50,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  color: const Color(0xFF0A0E1A),
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: _filters.map((filter) {
                      final isSelected = _selectedFilter == filter;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8, top: 8),
                        child: FilterChip(
                          label: Text(filter),
                          selected: isSelected,
                          onSelected: (_) =>
                              setState(() => _selectedFilter = filter),
                          backgroundColor: const Color(0xFF1C2333),
                          selectedColor: const Color(0xFF1A237E),
                          labelStyle: TextStyle(
                            color:
                                isSelected ? Colors.white : Colors.white54,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),

                // Device list
                Expanded(
                  child: devices.isEmpty
                      ? const Center(
                          child: Text(
                            'No devices found',
                            style: TextStyle(
                                color: Colors.white54, fontSize: 16),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredDevices.length,
                          itemBuilder: (context, index) {
                            final device = _filteredDevices[index];
                            return _deviceCard(device);
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _statusTile(String label, int count, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.15),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withOpacity(0.4)),
        ),
        child: Column(
          children: [
            Text(
              count.toString(),
              style: TextStyle(
                color: color,
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              label,
              style: TextStyle(color: color, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _deviceCard(Map<String, dynamic> device) {
    final color = _statusColor(device['status']);
    final connections = device['connectedTo'];
    int connectionCount = 0;
    if (connections is List) {
      connectionCount = connections.length;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1C2333),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.4), width: 1.5),
      ),
      child: ListTile(
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: color.withOpacity(0.15),
            borderRadius: BorderRadius.circular(12),
          ),
          child:
              Icon(_deviceIcon(device['type']), color: color, size: 26),
        ),
        title: Text(
          device['name'],
          style: const TextStyle(
              color: Colors.white, fontWeight: FontWeight.bold),
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            Text(
              device['ip'],
              style:
                  const TextStyle(color: Colors.white54, fontSize: 12),
            ),
            if (connectionCount > 0)
              Text(
                'Connected to $connectionCount device(s)',
                style: const TextStyle(
                    color: Colors.white38, fontSize: 11),
              ),
          ],
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                color: color,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                      color: color.withOpacity(0.6), blurRadius: 6)
                ],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              device['status'].toUpperCase(),
              style: TextStyle(
                  color: color,
                  fontSize: 10,
                  fontWeight: FontWeight.bold),
            ),
          ],
        ),
        onTap: () {
          if (device['status'] != 'ok') {
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) =>
                    ProblemsScreen(deviceId: device['id']),
              ),
            );
          }
        },
      ),
    );
  }
}
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SessionDevicesScreen extends StatefulWidget {
  final String sessionId;
  final String sessionName;
  const SessionDevicesScreen({
    super.key,
    required this.sessionId,
    required this.sessionName,
  });

  @override
  State<SessionDevicesScreen> createState() =>
      _SessionDevicesScreenState();
}

class _SessionDevicesScreenState
    extends State<SessionDevicesScreen> {
  List<Map<String, dynamic>> devices = [];
  bool _isLoading = true;
  String _selectedFilter = 'All';
  final List<String> _filters = [
    'All', 'Active', 'Unreachable', 'Unknown'
  ];

  @override
  void initState() {
    super.initState();
    _loadDevices();
  }

  Future<void> _loadDevices() async {
    setState(() => _isLoading = true);
    final data =
        await ApiService.getSessionDevices(widget.sessionId);
    setState(() {
      devices = data;
      _isLoading = false;
    });
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'active':
        return const Color(0xFF00C853);
      case 'unreachable':
        return const Color(0xFFE53935);
      case 'powered_off':
        return const Color(0xFF8E8E8E);
      default:
        return const Color(0xFFFFB300);
    }
  }

  IconData _deviceIcon(String? type) {
    switch (type) {
      case 'switch':
        return Icons.device_hub;
      case 'camera':
        return Icons.videocam_outlined;
      case 'dvr':
        return Icons.video_settings_outlined;
      case 'ap':
        return Icons.wifi;
      case 'pc':
        return Icons.computer;
      default:
        return Icons.devices_outlined;
    }
  }

  List<Map<String, dynamic>> get _filteredDevices {
    if (_selectedFilter == 'All') return devices;
    return devices
        .where((d) =>
            d['status']?.toLowerCase() ==
            _selectedFilter.toLowerCase())
        .toList();
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
          'Discovered Devices',
          style: TextStyle(
            color: Color(0xFF262626),
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
        iconTheme: const IconThemeData(color: Color(0xFF262626)),
        actions: [
          IconButton(
            icon:
                const Icon(Icons.refresh, color: Color(0xFF262626)),
            onPressed: _loadDevices,
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
          : Column(
              children: [
                // Session info bar
                Container(
                  color: const Color(0xFF833AB4).withOpacity(0.06),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 10),
                  child: Row(
                    children: [
                      const Icon(Icons.radar,
                          size: 14, color: Color(0xFF833AB4)),
                      const SizedBox(width: 8),
                      Text(
                        widget.sessionName,
                        style: const TextStyle(
                          color: Color(0xFF833AB4),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        '${devices.length} devices found',
                        style: const TextStyle(
                          color: Color(0xFF833AB4),
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),

                // Filter chips
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.symmetric(
                      vertical: 12, horizontal: 16),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: _filters.map((filter) {
                        final isSelected = _selectedFilter == filter;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: GestureDetector(
                            onTap: () => setState(
                                () => _selectedFilter = filter),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 16, vertical: 8),
                              decoration: BoxDecoration(
                                gradient: isSelected
                                    ? const LinearGradient(
                                        colors: [
                                          Color(0xFF833AB4),
                                          Color(0xFFE1306C),
                                        ],
                                      )
                                    : null,
                                color: isSelected
                                    ? null
                                    : const Color(0xFFF5F5F5),
                                borderRadius:
                                    BorderRadius.circular(20),
                              ),
                              child: Text(
                                filter,
                                style: TextStyle(
                                  color: isSelected
                                      ? Colors.white
                                      : const Color(0xFF262626),
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ),
                Divider(color: Colors.grey.shade200, height: 1),

                // Devices list
                Expanded(
                  child: _filteredDevices.isEmpty
                      ? const Center(
                          child: Text(
                            'No devices found',
                            style: TextStyle(
                                color: Color(0xFF8E8E8E),
                                fontSize: 16),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredDevices.length,
                          itemBuilder: (context, index) {
                            return _deviceCard(
                                _filteredDevices[index]);
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _deviceCard(Map<String, dynamic> device) {
    final color = _statusColor(device['status'] ?? '');

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
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
        border: Border.all(
          color: color.withOpacity(0.2),
          width: 1.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  _deviceIcon(device['device_type']),
                  color: color,
                  size: 22,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      device['hostname'] ??
                          device['ip_address'] ??
                          'Unknown',
                      style: const TextStyle(
                        color: Color(0xFF262626),
                        fontWeight: FontWeight.w600,
                        fontSize: 15,
                      ),
                    ),
                    Text(
                      device['ip_address'] ?? '',
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
                  color: color.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 5),
                    Text(
                      (device['status'] ?? '').toUpperCase(),
                      style: TextStyle(
                        color: color,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Divider(color: Colors.grey.shade100, height: 1),
          const SizedBox(height: 10),
          Row(
            children: [
              if (device['mac_address'] != null)
                _infoChip(Icons.memory_outlined,
                    device['mac_address'], const Color(0xFF8E8E8E)),
              if (device['switch_port'] != null) ...[
                const SizedBox(width: 8),
                _infoChip(Icons.settings_ethernet,
                    'Port ${device['switch_port']}',
                    const Color(0xFF8E8E8E)),
              ],
            ],
          ),
          if (device['response_time_ms'] != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                _infoChip(
                  Icons.speed_outlined,
                  '${device['response_time_ms']?.toStringAsFixed(1)} ms',
                  const Color(0xFF1E88E5),
                ),
                const SizedBox(width: 8),
                if (device['responds_to_ping'] == true)
                  _infoChip(Icons.check_circle_outline,
                      'Ping OK', const Color(0xFF00C853)),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _infoChip(IconData icon, String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 11,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
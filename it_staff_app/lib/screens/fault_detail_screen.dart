import 'package:flutter/material.dart';
import '../services/api_service.dart';

class FaultDetailScreen extends StatefulWidget {
  final Map<String, dynamic> fault;
  const FaultDetailScreen({super.key, required this.fault});

  @override
  State<FaultDetailScreen> createState() => _FaultDetailScreenState();
}

class _FaultDetailScreenState extends State<FaultDetailScreen> {
  late String _currentStatus;
  bool _isUpdating = false;
  final _notesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _currentStatus = widget.fault['status'] ??
        (widget.fault['is_resolved'] == true ? 'Resolved' : 'Open');
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'Open':
        return const Color(0xFFE53935);
      case 'In Progress':
        return const Color(0xFFFFB300);
      case 'Resolved':
        return const Color(0xFF00C853);
      default:
        return Colors.grey;
    }
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

  Future<void> _updateStatus(String newStatus) async {
    if (newStatus == 'Resolved') {
      _showResolveDialog();
      return;
    }
    setState(() => _isUpdating = true);
    final success = await ApiService.updateFaultStatus(
      widget.fault['id'].toString(),
      newStatus,
    );
    setState(() {
      _isUpdating = false;
      if (success) _currentStatus = newStatus;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
            success ? 'Status updated to $newStatus' : 'Failed to update'),
        backgroundColor:
            success ? _statusColor(newStatus) : Colors.red,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  void _showResolveDialog() {
    showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20)),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Mark as Resolved',
                style: TextStyle(
                  color: Color(0xFF262626),
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Add resolution notes (optional):',
                style: TextStyle(
                    color: Color(0xFF8E8E8E), fontSize: 13),
              ),
              const SizedBox(height: 12),
              Container(
                decoration: BoxDecoration(
                  color: const Color(0xFFFAFAFA),
                  borderRadius: BorderRadius.circular(12),
                  border:
                      Border.all(color: const Color(0xFFDBDBDB)),
                ),
                child: TextField(
                  controller: _notesController,
                  maxLines: 3,
                  style: const TextStyle(
                      color: Color(0xFF262626), fontSize: 14),
                  decoration: const InputDecoration(
                    hintText: 'What did you do to fix this?',
                    hintStyle:
                        TextStyle(color: Color(0xFF8E8E8E)),
                    border: InputBorder.none,
                    contentPadding: EdgeInsets.all(12),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF5F5F5),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Center(
                          child: Text('Cancel',
                              style: TextStyle(
                                  color: Color(0xFF8E8E8E),
                                  fontWeight: FontWeight.w600)),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: GestureDetector(
                      onTap: () async {
                        Navigator.pop(context);
                        setState(() => _isUpdating = true);
                        final success =
                            await ApiService.updateFaultStatus(
                          widget.fault['id'].toString(),
                          'Resolved',
                          notes: _notesController.text,
                        );
                        setState(() {
                          _isUpdating = false;
                          if (success) _currentStatus = 'Resolved';
                        });
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(success
                                ? 'Fault resolved!'
                                : 'Failed to update'),
                            backgroundColor: success
                                ? const Color(0xFF00C853)
                                : Colors.red,
                            behavior: SnackBarBehavior.floating,
                            shape: RoundedRectangleBorder(
                                borderRadius:
                                    BorderRadius.circular(10)),
                          ),
                        );
                      },
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                            vertical: 12),
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(colors: [
                            Color(0xFF00C853),
                            Color(0xFF00897B)
                          ]),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Center(
                          child: Text('Resolve',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600)),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final fault = widget.fault;
    final severityColor = _severityColor(fault['severity'] ?? '');
    final steps = fault['troubleshooting_steps'] as List? ?? [];
    final affectedIps = fault['affected_ips'] as List? ?? [];

    return Scaffold(
      backgroundColor: const Color(0xFFFAFAFA),
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        title: const Text(
          'Fault Details',
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
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Fault header card
            Container(
              width: double.infinity,
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
                  Container(
                    height: 5,
                    decoration: BoxDecoration(
                      color: _statusColor(_currentStatus),
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
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color:
                                    severityColor.withOpacity(0.1),
                                borderRadius:
                                    BorderRadius.circular(12),
                              ),
                              child: Icon(Icons.bug_report_rounded,
                                  color: severityColor, size: 24),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    (fault['fault_type'] ?? '')
                                        .replaceAll('_', ' '),
                                    style: const TextStyle(
                                      color: Color(0xFF262626),
                                      fontSize: 17,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets
                                            .symmetric(
                                            horizontal: 8,
                                            vertical: 3),
                                        decoration: BoxDecoration(
                                          color: severityColor
                                              .withOpacity(0.1),
                                          borderRadius:
                                              BorderRadius.circular(
                                                  20),
                                        ),
                                        child: Text(
                                          (fault['severity'] ?? '')
                                              .toUpperCase(),
                                          style: TextStyle(
                                            color: severityColor,
                                            fontSize: 10,
                                            fontWeight:
                                                FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Container(
                                        padding: const EdgeInsets
                                            .symmetric(
                                            horizontal: 8,
                                            vertical: 3),
                                        decoration: BoxDecoration(
                                          color: _statusColor(
                                                  _currentStatus)
                                              .withOpacity(0.1),
                                          borderRadius:
                                              BorderRadius.circular(
                                                  20),
                                          border: Border.all(
                                            color: _statusColor(
                                                    _currentStatus)
                                                .withOpacity(0.3),
                                          ),
                                        ),
                                        child: Text(
                                          _currentStatus
                                              .toUpperCase(),
                                          style: TextStyle(
                                            color: _statusColor(
                                                _currentStatus),
                                            fontSize: 10,
                                            fontWeight:
                                                FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Text(
                          fault['description'] ?? '',
                          style: const TextStyle(
                            color: Color(0xFF8E8E8E),
                            fontSize: 14,
                            height: 1.5,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Divider(color: Colors.grey.shade100),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Icon(Icons.router_outlined,
                                size: 14,
                                color: Colors.grey.shade400),
                            const SizedBox(width: 6),
                            Text(
                              fault['device_name'] ??
                                  fault['ip_address'] ??
                                  'Unknown',
                              style: const TextStyle(
                                  color: Color(0xFF8E8E8E),
                                  fontSize: 13),
                            ),
                            if (fault['switch_port'] != null) ...[
                              const SizedBox(width: 8),
                              Icon(Icons.settings_ethernet,
                                  size: 14,
                                  color: Colors.grey.shade400),
                              const SizedBox(width: 4),
                              Text(
                                'Port ${fault['switch_port']}',
                                style: const TextStyle(
                                    color: Color(0xFF8E8E8E),
                                    fontSize: 13),
                              ),
                            ],
                            const Spacer(),
                            Icon(Icons.access_time,
                                size: 13,
                                color: Colors.grey.shade400),
                            const SizedBox(width: 4),
                            Text(
                              fault['detected_at'] ?? '',
                              style: const TextStyle(
                                  color: Color(0xFFB0B0B0),
                                  fontSize: 12),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Affected IPs
            if (affectedIps.isNotEmpty) ...[
              Container(
                width: double.infinity,
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
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Affected IP Addresses',
                      style: TextStyle(
                        color: Color(0xFF262626),
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: affectedIps.map((ip) {
                        return Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: severityColor.withOpacity(0.08),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                                color:
                                    severityColor.withOpacity(0.3)),
                          ),
                          child: Text(
                            ip.toString(),
                            style: TextStyle(
                              color: severityColor,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],

            // Resolution notes
            if (_currentStatus == 'Resolved' &&
                fault['resolution_notes'] != null &&
                fault['resolution_notes']
                    .toString()
                    .isNotEmpty) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF00C853).withOpacity(0.06),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                      color: const Color(0xFF00C853)
                          .withOpacity(0.3)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.check_circle,
                            color: Color(0xFF00C853), size: 16),
                        SizedBox(width: 8),
                        Text(
                          'Resolution Notes',
                          style: TextStyle(
                            color: Color(0xFF00C853),
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      fault['resolution_notes'],
                      style: const TextStyle(
                        color: Color(0xFF00C853),
                        fontSize: 13,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],

            // Steps
            const Padding(
              padding: EdgeInsets.only(left: 4, bottom: 12),
              child: Text(
                'Troubleshooting Steps',
                style: TextStyle(
                  color: Color(0xFF262626),
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            ...steps.asMap().entries.map((entry) {
              final index = entry.key;
              final step = entry.value;
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
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 28,
                      height: 28,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [
                            Color(0xFF833AB4),
                            Color(0xFFE1306C)
                          ],
                        ),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Center(
                        child: Text(
                          '${index + 1}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        step.toString(),
                        style: const TextStyle(
                          color: Color(0xFF262626),
                          fontSize: 14,
                          height: 1.4,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
            const SizedBox(height: 20),

            // Action buttons
            if (_isUpdating)
              const Center(
                child: CircularProgressIndicator(
                  valueColor: AlwaysStoppedAnimation<Color>(
                      Color(0xFFE1306C)),
                ),
              )
            else if (_currentStatus == 'Open')
              _actionButton(
                label: 'Mark as In Progress',
                icon: Icons.play_arrow_rounded,
                colors: [
                  const Color(0xFFFFB300),
                  const Color(0xFFFF8F00)
                ],
                onTap: () => _updateStatus('In Progress'),
              )
            else if (_currentStatus == 'In Progress')
              Column(
                children: [
                  _actionButton(
                    label: 'Mark as Resolved',
                    icon: Icons.check_circle_rounded,
                    colors: [
                      const Color(0xFF00C853),
                      const Color(0xFF00897B)
                    ],
                    onTap: () => _updateStatus('Resolved'),
                  ),
                  const SizedBox(height: 10),
                  _actionButton(
                    label: 'Reopen Fault',
                    icon: Icons.refresh_rounded,
                    colors: [
                      const Color(0xFF8E8E8E),
                      const Color(0xFF616161)
                    ],
                    onTap: () => _updateStatus('Open'),
                  ),
                ],
              )
            else if (_currentStatus == 'Resolved')
              Column(
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF00C853).withOpacity(0.08),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                          color: const Color(0xFF00C853)
                              .withOpacity(0.3)),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.check_circle_rounded,
                            color: Color(0xFF00C853), size: 22),
                        SizedBox(width: 10),
                        Text(
                          'Fault Resolved ✓',
                          style: TextStyle(
                            color: Color(0xFF00C853),
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  _actionButton(
                    label: 'Reopen Fault',
                    icon: Icons.refresh_rounded,
                    colors: [
                      const Color(0xFF8E8E8E),
                      const Color(0xFF616161)
                    ],
                    onTap: () => _updateStatus('Open'),
                  ),
                ],
              ),
            const SizedBox(height: 30),
          ],
        ),
      ),
    );
  }

  Widget _actionButton({
    required String label,
    required IconData icon,
    required List<Color> colors,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: double.infinity,
        height: 52,
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: colors),
          borderRadius: BorderRadius.circular(14),
          boxShadow: [
            BoxShadow(
              color: colors[0].withOpacity(0.3),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: Colors.white, size: 20),
            const SizedBox(width: 8),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
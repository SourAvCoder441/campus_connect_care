import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'fault_detail_screen.dart';

class FaultsScreen extends StatefulWidget {
  final String? sessionId;
  final String? sessionName;
  final String? initialFilter;
  const FaultsScreen({
    super.key,
    this.sessionId,
    this.sessionName,
    this.initialFilter,
  });

  @override
  State<FaultsScreen> createState() => _FaultsScreenState();
}

class _FaultsScreenState extends State<FaultsScreen> {
  List<Map<String, dynamic>> faults = [];
  bool _isLoading = true;
  late String _selectedSeverity;
  String _selectedStatus = 'All';

  final List<String> _severityFilters = [
    'All', 'Critical', 'High', 'Medium', 'Low'
  ];
  final List<String> _statusFilters = [
    'All', 'Open', 'In Progress', 'Resolved'
  ];

  @override
  void initState() {
    super.initState();
    _selectedSeverity = widget.initialFilter ?? 'All';
    _loadFaults();
  }

  Future<void> _loadFaults() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getFaults(
      sessionId: widget.sessionId,
      resolved: 'all',
    );
    setState(() {
      faults = data;
      _isLoading = false;
    });
  }

  List<Map<String, dynamic>> get _filteredFaults {
    var list = faults;
    if (_selectedSeverity != 'All') {
      list = list
          .where((f) =>
              f['severity']?.toLowerCase() ==
              _selectedSeverity.toLowerCase())
          .toList();
    }
    if (_selectedStatus != 'All') {
      list = list
          .where((f) => f['status'] == _selectedStatus)
          .toList();
    }
    return list;
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

  IconData _severityIcon(String severity) {
    switch (severity) {
      case 'critical':
        return Icons.error_rounded;
      case 'high':
        return Icons.warning_amber_rounded;
      case 'medium':
        return Icons.info_rounded;
      case 'low':
        return Icons.check_circle_outline;
      default:
        return Icons.circle_outlined;
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
        title: Text(
          widget.sessionId != null ? 'Session Faults' : 'All Faults',
          style: const TextStyle(
            color: Color(0xFF262626),
            fontWeight: FontWeight.bold,
            fontSize: 18,
          ),
        ),
        iconTheme: const IconThemeData(color: Color(0xFF262626)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF262626)),
            onPressed: _loadFaults,
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
                Container(
                  color: Colors.white,
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Severity filters
                      const Text(
                        'Severity',
                        style: TextStyle(
                          color: Color(0xFF8E8E8E),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: _severityFilters.map((filter) {
                            final isSelected =
                                _selectedSeverity == filter;
                            return Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: GestureDetector(
                                onTap: () => setState(
                                    () => _selectedSeverity = filter),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 16, vertical: 7),
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
                      const SizedBox(height: 10),

                      // Status filters
                      const Text(
                        'Status',
                        style: TextStyle(
                          color: Color(0xFF8E8E8E),
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: _statusFilters.map((status) {
                            final isSelected =
                                _selectedStatus == status;
                            Color statusColor = const Color(0xFF8E8E8E);
                            if (status == 'Open')
                              statusColor = const Color(0xFFE53935);
                            if (status == 'In Progress')
                              statusColor = const Color(0xFFFFB300);
                            if (status == 'Resolved')
                              statusColor = const Color(0xFF00C853);

                            return Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: GestureDetector(
                                onTap: () => setState(
                                    () => _selectedStatus = status),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 16, vertical: 7),
                                  decoration: BoxDecoration(
                                    color: isSelected
                                        ? statusColor.withOpacity(0.12)
                                        : const Color(0xFFF5F5F5),
                                    borderRadius:
                                        BorderRadius.circular(20),
                                    border: isSelected
                                        ? Border.all(
                                            color: statusColor
                                                .withOpacity(0.4))
                                        : null,
                                  ),
                                  child: Text(
                                    status,
                                    style: TextStyle(
                                      color: isSelected
                                          ? statusColor
                                          : const Color(0xFF8E8E8E),
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
                      const SizedBox(height: 12),
                    ],
                  ),
                ),
                Divider(color: Colors.grey.shade200, height: 1),

                // Results count
                Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      Text(
                        '${_filteredFaults.length} fault(s) found',
                        style: const TextStyle(
                          color: Color(0xFF8E8E8E),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),

                // Faults list
                Expanded(
                  child: _filteredFaults.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.check_circle_outline,
                                  size: 60,
                                  color: Colors.grey.shade300),
                              const SizedBox(height: 12),
                              const Text(
                                'No faults found!',
                                style: TextStyle(
                                  color: Color(0xFF8E8E8E),
                                  fontSize: 16,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadFaults,
                          color: const Color(0xFFE1306C),
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(
                                16, 4, 16, 16),
                            itemCount: _filteredFaults.length,
                            itemBuilder: (context, index) {
                              return _faultCard(
                                  _filteredFaults[index]);
                            },
                          ),
                        ),
                ),
              ],
            ),
    );
  }

  Widget _faultCard(Map<String, dynamic> fault) {
    final severityColor = _severityColor(fault['severity'] ?? '');
    final status = fault['status'] ?? 'Open';
    final statusColor = _statusColor(status);
    final isResolved = status == 'Resolved';

    return GestureDetector(
      onTap: () async {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => FaultDetailScreen(fault: fault),
          ),
        );
        _loadFaults();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: isResolved ? const Color(0xFFFAFAFA) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color:
                  Colors.black.withOpacity(isResolved ? 0.02 : 0.05),
              blurRadius: 12,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          children: [
            // Severity bar
            Container(
              height: 4,
              decoration: BoxDecoration(
                color: isResolved
                    ? Colors.grey.shade300
                    : severityColor,
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
                      Icon(
                        _severityIcon(fault['severity'] ?? ''),
                        color: isResolved
                            ? Colors.grey.shade400
                            : severityColor,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          (fault['fault_type'] ?? '')
                              .replaceAll('_', ' '),
                          style: TextStyle(
                            color: isResolved
                                ? const Color(0xFF8E8E8E)
                                : const Color(0xFF262626),
                            fontWeight: FontWeight.bold,
                            fontSize: 15,
                            decoration: isResolved
                                ? TextDecoration.lineThrough
                                : null,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Status badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: statusColor.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                              color: statusColor.withOpacity(0.3)),
                        ),
                        child: Text(
                          status.toUpperCase(),
                          style: TextStyle(
                            color: statusColor,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      // Severity badge
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: severityColor.withOpacity(0.08),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          (fault['severity'] ?? '').toUpperCase(),
                          style: TextStyle(
                            color: severityColor,
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(Icons.router_outlined,
                          size: 13,
                          color: Colors.grey.shade400),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          fault['device_name'] ??
                              fault['ip_address'] ??
                              'Unknown device',
                          style: const TextStyle(
                            color: Color(0xFF8E8E8E),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(
                    fault['description'] ?? '',
                    style: const TextStyle(
                      color: Color(0xFFB0B0B0),
                      fontSize: 12,
                      height: 1.4,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(Icons.access_time,
                          size: 12, color: Colors.grey.shade400),
                      const SizedBox(width: 4),
                      Text(
                        fault['detected_at'] ?? '',
                        style: const TextStyle(
                          color: Color(0xFFB0B0B0),
                          fontSize: 11,
                        ),
                      ),
                      const Spacer(),
                      if (fault['switch_port'] != null)
                        Text(
                          'Port ${fault['switch_port']}',
                          style: const TextStyle(
                            color: Color(0xFFB0B0B0),
                            fontSize: 11,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
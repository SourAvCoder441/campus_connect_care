import 'package:flutter/material.dart';
import 'problem_detail_screen.dart';
import '../services/api_service.dart';

class ProblemsScreen extends StatefulWidget {
  final String? deviceId;
  const ProblemsScreen({super.key, this.deviceId});

  @override
  State<ProblemsScreen> createState() => _ProblemsScreenState();
}

class _ProblemsScreenState extends State<ProblemsScreen> {
  String _selectedStatus = 'All';
  final List<String> _statusFilters = ['All', 'Open', 'In Progress', 'Resolved'];
  List<Map<String, dynamic>> problems = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadProblems();
  }

  Future<void> _loadProblems() async {
    setState(() => _isLoading = true);
    final data = await ApiService.getProblems();
    setState(() {
      problems = data;
      _isLoading = false;
    });
  }

  List<Map<String, dynamic>> get _filteredProblems {
    var list = problems;
    if (widget.deviceId != null) {
      list = list.where((p) => p['deviceId'] == widget.deviceId).toList();
    }
    if (_selectedStatus != 'All') {
      list = list.where((p) => p['status'] == _selectedStatus).toList();
    }
    return list;
  }

  Color _severityColor(String severity) {
    switch (severity) {
      case 'critical':
        return const Color(0xFFFF1744);
      case 'warning':
        return const Color(0xFFFFD600);
      default:
        return const Color(0xFF00C853);
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'Open':
        return const Color(0xFFFF1744);
      case 'In Progress':
        return const Color(0xFFFFD600);
      case 'Resolved':
        return const Color(0xFF00C853);
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0E1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A237E),
        title: Text(
          widget.deviceId != null ? 'Device Problems' : 'All Problems',
          style: const TextStyle(
              color: Colors.white, fontWeight: FontWeight.bold),
        ),
        iconTheme: const IconThemeData(color: Colors.white),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.white),
            onPressed: _loadProblems,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: Colors.white))
          : Column(
              children: [
                // Status filter
                Container(
                  height: 50,
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  color: const Color(0xFF1C2333),
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    children: _statusFilters.map((status) {
                      final isSelected = _selectedStatus == status;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8, top: 8),
                        child: FilterChip(
                          label: Text(status),
                          selected: isSelected,
                          onSelected: (_) =>
                              setState(() => _selectedStatus = status),
                          backgroundColor: const Color(0xFF0A0E1A),
                          selectedColor: const Color(0xFF1A237E),
                          labelStyle: TextStyle(
                            color: isSelected
                                ? Colors.white
                                : Colors.white54,
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),

                // Problems list
                Expanded(
                  child: _filteredProblems.isEmpty
                      ? const Center(
                          child: Text(
                            'No problems found',
                            style: TextStyle(
                                color: Colors.white54, fontSize: 16),
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(16),
                          itemCount: _filteredProblems.length,
                          itemBuilder: (context, index) {
                            final problem = _filteredProblems[index];
                            return _problemCard(problem);
                          },
                        ),
                ),
              ],
            ),
    );
  }

  Widget _problemCard(Map<String, dynamic> problem) {
    final severityColor = _severityColor(problem['severity']);
    final statusColor = _statusColor(problem['status']);

    return GestureDetector(
      onTap: () async {
        await Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ProblemDetailScreen(problem: problem),
          ),
        );
        _loadProblems();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: const Color(0xFF1C2333),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: severityColor.withOpacity(0.4), width: 1.5),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(Icons.warning_amber,
                      color: severityColor, size: 20),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      problem['type'],
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                          color: statusColor.withOpacity(0.5)),
                    ),
                    child: Text(
                      problem['status'],
                      style: TextStyle(
                          color: statusColor,
                          fontSize: 11,
                          fontWeight: FontWeight.bold),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                problem['deviceName'],
                style:
                    const TextStyle(color: Colors.white70, fontSize: 13),
              ),
              const SizedBox(height: 4),
              Text(
                problem['description'],
                style: const TextStyle(
                    color: Colors.white38, fontSize: 12),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  const Icon(Icons.person,
                      color: Colors.white38, size: 14),
                  const SizedBox(width: 4),
                  Text(
                    problem['assignedTo'],
                    style: const TextStyle(
                        color: Colors.white38, fontSize: 12),
                  ),
                  const Spacer(),
                  const Icon(Icons.access_time,
                      color: Colors.white38, size: 14),
                  const SizedBox(width: 4),
                  Text(
                    problem['time'],
                    style: const TextStyle(
                        color: Colors.white38, fontSize: 12),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
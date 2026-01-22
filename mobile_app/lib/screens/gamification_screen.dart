import 'package:flutter/material.dart';
import '../api/api_service.dart';

class GamificationScreen extends StatefulWidget {
  final ApiService api;

  const GamificationScreen({super.key, required this.api});

  @override
  State<GamificationScreen> createState() => _GamificationScreenState();
}

class _GamificationScreenState extends State<GamificationScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isLoading = true;

  // Status data
  Map<String, dynamic> _status = {};
  List<dynamic> _leaderboard = [];
  List<dynamic> _unlockedAchievements = [];
  List<dynamic> _lockedAchievements = [];
  List<dynamic> _challenges = [];
  String _selectedPeriod = 'weekly';

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _loadData();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);

    try {
      final results = await Future.wait([
        widget.api.getGamificationStatus(),
        widget.api.getLeaderboard(period: _selectedPeriod),
        widget.api.getAchievements(),
        widget.api.getChallenges(),
      ]);

      setState(() {
        if (results[0]['success'] == true) {
          _status = results[0];
        }
        if (results[1]['success'] == true) {
          _leaderboard = results[1]['leaderboard'] ?? [];
        }
        if (results[2]['success'] == true) {
          _unlockedAchievements = results[2]['unlocked'] ?? [];
          _lockedAchievements = results[2]['locked'] ?? [];
        }
        if (results[3]['success'] == true) {
          _challenges = results[3]['challenges'] ?? [];
        }
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Error al cargar datos')),
        );
      }
    }
  }

  Future<void> _loadLeaderboard() async {
    final result = await widget.api.getLeaderboard(period: _selectedPeriod);
    if (result['success'] == true) {
      setState(() => _leaderboard = result['leaderboard'] ?? []);
    }
  }

  Future<void> _joinChallenge(int challengeId) async {
    final result = await widget.api.joinChallenge(challengeId);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message'] ?? 'Acción completada'),
          backgroundColor:
              result['success'] == true ? Colors.green : Colors.red,
        ),
      );
      if (result['success'] == true) {
        _loadData();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Gamificación'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black87,
        elevation: 0,
        bottom: TabBar(
          controller: _tabController,
          labelColor: Theme.of(context).primaryColor,
          unselectedLabelColor: Colors.grey,
          indicatorColor: Theme.of(context).primaryColor,
          tabs: const [
            Tab(icon: Icon(Icons.emoji_events), text: 'Mi Progreso'),
            Tab(icon: Icon(Icons.leaderboard), text: 'Ranking'),
            Tab(icon: Icon(Icons.flag), text: 'Retos'),
          ],
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : TabBarView(
              controller: _tabController,
              children: [
                _buildProgressTab(),
                _buildLeaderboardTab(),
                _buildChallengesTab(),
              ],
            ),
    );
  }

  Widget _buildProgressTab() {
    final level = _status['level'] ?? 1;
    final xp = _status['xp'] ?? 0;
    final xpToNext = _status['xp_to_next_level'] ?? 100;
    final streak = _status['streak'] ?? 0;
    final progress = xpToNext > 0 ? (xp / xpToNext).clamp(0.0, 1.0) : 0.0;

    return RefreshIndicator(
      onRefresh: _loadData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Level Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.indigo.shade600,
                    Colors.purple.shade600,
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.indigo.withOpacity(0.3),
                    blurRadius: 15,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Row(
                    children: [
                      Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.2),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 3),
                        ),
                        child: Center(
                          child: Text(
                            '$level',
                            style: const TextStyle(
                              fontSize: 36,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 20),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Nivel',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 14,
                              ),
                            ),
                            Text(
                              _getLevelTitle(level),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                const Icon(Icons.local_fire_department,
                                    color: Colors.orange, size: 20),
                                const SizedBox(width: 4),
                                Text(
                                  '$streak días de racha',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 14,
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  // XP Progress Bar
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '$xp XP',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          Text(
                            '$xpToNext XP para nivel ${level + 1}',
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(10),
                        child: LinearProgressIndicator(
                          value: progress as double,
                          minHeight: 10,
                          backgroundColor: Colors.white.withOpacity(0.3),
                          valueColor:
                              const AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: 24),

            // Achievements Section
            const Text(
              'Logros Desbloqueados',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),

            if (_unlockedAchievements.isEmpty)
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Center(
                  child: Text(
                    '¡Aún no has desbloqueado logros!\nSigue entrenando para conseguir tu primer logro.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Colors.grey),
                  ),
                ),
              )
            else
              SizedBox(
                height: 120,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: _unlockedAchievements.length,
                  itemBuilder: (context, index) {
                    final achievement = _unlockedAchievements[index];
                    return _buildAchievementCard(achievement, unlocked: true);
                  },
                ),
              ),

            const SizedBox(height: 24),

            // Locked Achievements
            if (_lockedAchievements.isNotEmpty) ...[
              const Text(
                'Próximos Logros',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 120,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: _lockedAchievements.length.clamp(0, 5),
                  itemBuilder: (context, index) {
                    final achievement = _lockedAchievements[index];
                    return _buildAchievementCard(achievement, unlocked: false);
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAchievementCard(Map<String, dynamic> achievement,
      {required bool unlocked}) {
    return Container(
      width: 100,
      margin: const EdgeInsets.only(right: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: unlocked
            ? Border.all(color: Colors.amber, width: 2)
            : Border.all(color: Colors.grey.shade200),
        boxShadow: unlocked
            ? [
                BoxShadow(
                  color: Colors.amber.withOpacity(0.2),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            achievement['icon'] ?? '🏆',
            style: TextStyle(
              fontSize: 32,
              color: unlocked ? null : Colors.grey,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            achievement['name'] ?? '',
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: unlocked ? Colors.black87 : Colors.grey,
            ),
          ),
          Text(
            '+${achievement['xp_reward'] ?? 0} XP',
            style: TextStyle(
              fontSize: 10,
              color: unlocked ? Colors.indigo : Colors.grey,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLeaderboardTab() {
    return Column(
      children: [
        // Period Selector
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          color: Colors.white,
          child: Row(
            children: [
              _buildPeriodChip('weekly', 'Semanal'),
              const SizedBox(width: 8),
              _buildPeriodChip('monthly', 'Mensual'),
              const SizedBox(width: 8),
              _buildPeriodChip('all_time', 'Total'),
            ],
          ),
        ),

        // Leaderboard List
        Expanded(
          child: RefreshIndicator(
            onRefresh: _loadLeaderboard,
            child: _leaderboard.isEmpty
                ? const Center(
                    child: Text('No hay datos de ranking'),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _leaderboard.length,
                    itemBuilder: (context, index) {
                      final entry = _leaderboard[index];
                      return _buildLeaderboardEntry(entry, index + 1);
                    },
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildPeriodChip(String value, String label) {
    final isSelected = _selectedPeriod == value;
    return GestureDetector(
      onTap: () {
        setState(() => _selectedPeriod = value);
        _loadLeaderboard();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: isSelected ? Theme.of(context).primaryColor : Colors.grey.shade100,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? Colors.white : Colors.black87,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          ),
        ),
      ),
    );
  }

  Widget _buildLeaderboardEntry(Map<String, dynamic> entry, int position) {
    final isCurrentUser = entry['is_current_user'] == true;
    
    Color? medalColor;
    IconData? medalIcon;
    if (position == 1) {
      medalColor = Colors.amber;
      medalIcon = Icons.emoji_events;
    } else if (position == 2) {
      medalColor = Colors.grey.shade400;
      medalIcon = Icons.emoji_events;
    } else if (position == 3) {
      medalColor = Colors.brown.shade300;
      medalIcon = Icons.emoji_events;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isCurrentUser ? Colors.indigo.shade50 : Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: isCurrentUser
            ? Border.all(color: Colors.indigo, width: 2)
            : null,
      ),
      child: Row(
        children: [
          // Position
          SizedBox(
            width: 40,
            child: medalIcon != null
                ? Icon(medalIcon, color: medalColor, size: 28)
                : Text(
                    '#$position',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.grey.shade600,
                    ),
                  ),
          ),

          // Avatar
          CircleAvatar(
            radius: 20,
            backgroundColor: Colors.indigo.shade100,
            child: Text(
              (entry['name'] ?? 'U')[0].toUpperCase(),
              style: TextStyle(
                color: Colors.indigo.shade600,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),

          const SizedBox(width: 12),

          // Name
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry['name'] ?? 'Usuario',
                  style: TextStyle(
                    fontWeight: isCurrentUser ? FontWeight.bold : FontWeight.w500,
                  ),
                ),
                Text(
                  'Nivel ${entry['level'] ?? 1}',
                  style: const TextStyle(
                    color: Colors.grey,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),

          // XP
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${entry['xp'] ?? 0}',
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
              const Text(
                'XP',
                style: TextStyle(
                  color: Colors.grey,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildChallengesTab() {
    return RefreshIndicator(
      onRefresh: _loadData,
      child: _challenges.isEmpty
          ? const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.flag_outlined, size: 64, color: Colors.grey),
                    SizedBox(height: 16),
                    Text(
                      'No hay retos disponibles',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.grey,
                      ),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Vuelve pronto para ver nuevos retos',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _challenges.length,
              itemBuilder: (context, index) {
                final challenge = _challenges[index];
                return _buildChallengeCard(challenge);
              },
            ),
    );
  }

  Widget _buildChallengeCard(Map<String, dynamic> challenge) {
    final isJoined = challenge['is_joined'] == true;
    final progress = challenge['progress'] ?? 0;
    final goal = challenge['goal'] ?? 1;
    final progressPercent = goal > 0 ? (progress / goal).clamp(0.0, 1.0) : 0.0;
    final daysLeft = challenge['days_left'] ?? 0;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.purple.shade50,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  challenge['icon'] ?? '🎯',
                  style: const TextStyle(fontSize: 24),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      challenge['name'] ?? 'Reto',
                      style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 16,
                      ),
                    ),
                    Text(
                      challenge['description'] ?? '',
                      style: const TextStyle(
                        color: Colors.grey,
                        fontSize: 13,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.amber.shade50,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  '+${challenge['xp_reward'] ?? 0} XP',
                  style: TextStyle(
                    color: Colors.amber.shade800,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),

          if (isJoined) ...[
            const SizedBox(height: 16),
            // Progress Bar
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Progreso: $progress / $goal',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                Text(
                  '$daysLeft días restantes',
                  style: const TextStyle(
                    fontSize: 12,
                    color: Colors.grey,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: progressPercent as double,
                minHeight: 8,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation<Color>(
                  progressPercent >= 1.0 ? Colors.green : Colors.purple,
                ),
              ),
            ),
          ] else ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Text(
                  '${challenge['participants'] ?? 0} participantes',
                  style: const TextStyle(
                    color: Colors.grey,
                    fontSize: 12,
                  ),
                ),
                const Spacer(),
                ElevatedButton(
                  onPressed: () => _joinChallenge(challenge['id']),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.purple,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                  ),
                  child: const Text('Unirse'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  String _getLevelTitle(int level) {
    if (level <= 5) return 'Principiante';
    if (level <= 10) return 'Deportista';
    if (level <= 20) return 'Atleta';
    if (level <= 30) return 'Experto';
    if (level <= 50) return 'Maestro';
    return 'Leyenda';
  }
}

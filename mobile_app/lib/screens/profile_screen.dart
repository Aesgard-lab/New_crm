import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../models/models.dart';
import 'package:intl/intl.dart';
import 'billing_screen.dart';
import 'history_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final api = Provider.of<ApiService>(context);
    final client = api.currentClient;

    if (client == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: CustomScrollView(
        slivers: [
          // Header with profile picture
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            backgroundColor: const Color(0xFF0F172A),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: const BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
                  ),
                ),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 40),
                    Hero(
                      tag: 'profile_photo',
                      child: CircleAvatar(
                        radius: 50,
                        backgroundColor: Colors.white24,
                        backgroundImage: (client.photo.isNotEmpty)
                            ? NetworkImage(client.photo)
                            : null,
                        child: (client.photo.isEmpty)
                            ? Text(
                                client.firstName.substring(0, 1),
                                style: const TextStyle(
                                  fontSize: 36,
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                ),
                              )
                            : null,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      client.fullName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    Text(
                      client.gymName,
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),

          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Personal Information Section
                  _SectionTitle(title: 'Información Personal'),
                  const SizedBox(height: 12),
                  _InfoCard(
                    children: [
                      _InfoRow(
                        icon: Icons.email_outlined,
                        label: 'Email',
                        value: client.email,
                      ),
                      const Divider(height: 24),
                      _InfoRow(
                        icon: Icons.phone_outlined,
                        label: 'Teléfono',
                        value: client.phone.isNotEmpty ? client.phone : 'No registrado',
                      ),
                      const Divider(height: 24),
                      _InfoRow(
                        icon: Icons.badge_outlined,
                        label: 'ID de Cliente',
                        value: '#${client.id.toString().padLeft(6, '0')}',
                      ),
                    ],
                  ),

                  const SizedBox(height: 24),

                  // Membership Section
                  _SectionTitle(title: 'Membresía'),
                  const SizedBox(height: 12),
                  _MembershipCard(membership: client.activeMembership),

                  const SizedBox(height: 24),

                  // Access Code Section
                  _SectionTitle(title: 'Código de Acceso'),
                  const SizedBox(height: 12),
                  _AccessCodeCard(accessCode: client.accessCode),

                  const SizedBox(height: 24),

                  // Stats Section
                  _SectionTitle(title: 'Estadísticas'),
                  const SizedBox(height: 12),
                  _StatsCard(stats: client.stats),

                  const SizedBox(height: 24),

                  // Settings Section
                  _SectionTitle(title: 'Configuración'),
                  const SizedBox(height: 12),
                  _InfoCard(
                    children: [
                      _SettingsRow(
                        icon: Icons.history,
                        label: 'Historial de Clases',
                        onTap: () {
                          Navigator.push(context, MaterialPageRoute(builder: (c) => const HistoryScreen()));
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.receipt_long_outlined,
                        label: 'Facturación',
                        onTap: () {
                          Navigator.push(context, MaterialPageRoute(builder: (c) => const BillingScreen()));
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.notifications_outlined,
                        label: 'Notificaciones',
                        onTap: () {
                          // TODO: Navigate to notifications settings
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.lock_outline,
                        label: 'Cambiar Contraseña',
                        onTap: () {
                          // TODO: Navigate to change password
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.help_outline,
                        label: 'Ayuda y Soporte',
                        onTap: () {
                          // TODO: Navigate to help
                        },
                      ),
                    ],
                  ),

                  const SizedBox(height: 24),

                  // Logout Button
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        showDialog(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('Cerrar Sesión'),
                            content: const Text('¿Estás seguro que deseas cerrar sesión?'),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx),
                                child: const Text('Cancelar'),
                              ),
                              TextButton(
                                onPressed: () {
                                  api.logout();
                                  Navigator.of(context).pushNamedAndRemoveUntil(
                                    '/search',
                                    (route) => false,
                                  );
                                },
                                child: const Text(
                                  'Cerrar Sesión',
                                  style: TextStyle(color: Colors.red),
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red[50],
                        foregroundColor: Colors.red,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        elevation: 0,
                      ),
                      child: const Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.logout),
                          SizedBox(width: 8),
                          Text(
                            'Cerrar Sesión',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final String title;

  const _SectionTitle({required this.title});

  @override
  Widget build(BuildContext context) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.bold,
        color: Color(0xFF0F172A),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final List<Widget> children;

  const _InfoCard({required this.children});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
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
      child: Column(children: children),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _InfoRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: const Color(0xFF0F172A).withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(icon, size: 20, color: const Color(0xFF0F172A)),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF0F172A),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SettingsRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _SettingsRow({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A).withOpacity(0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 20, color: const Color(0xFF0F172A)),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: Color(0xFF0F172A),
              ),
            ),
          ),
          Icon(Icons.chevron_right, color: Colors.grey[400]),
        ],
      ),
    );
  }
}

class _MembershipCard extends StatelessWidget {
  final Map<String, dynamic>? membership;

  const _MembershipCard({this.membership});

  @override
  Widget build(BuildContext context) {
    if (membership == null) {
      return _InfoCard(
        children: [
          Text(
            'No tienes una membresía activa',
            style: TextStyle(color: Colors.grey[600]),
          ),
        ],
      );
    }

    final planName = membership!['plan_name'] ?? 'Plan';
    final expiresAt = membership!['expires_at'];
    final status = membership!['status'] ?? 'active';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFF0F172A).withOpacity(0.3),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                planName,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: status == 'active' ? Colors.green : Colors.orange,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  status == 'active' ? 'Activa' : 'Pendiente',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          if (expiresAt != null) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                const Icon(Icons.calendar_today, color: Colors.white70, size: 16),
                const SizedBox(width: 8),
                Text(
                  'Vence: $expiresAt',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _AccessCodeCard extends StatelessWidget {
  final String accessCode;

  const _AccessCodeCard({required this.accessCode});

  @override
  Widget build(BuildContext context) {
    if (accessCode.isEmpty) {
      return _InfoCard(
        children: [
          Text(
            'No tienes código de acceso asignado',
            style: TextStyle(color: Colors.grey[600]),
          ),
        ],
      );
    }

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.grey[200]!, width: 2),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          const Icon(
            Icons.qr_code_2,
            size: 48,
            color: Color(0xFF0F172A),
          ),
          const SizedBox(height: 16),
          Text(
            accessCode,
            style: const TextStyle(
              fontSize: 36,
              fontWeight: FontWeight.bold,
              letterSpacing: 8,
              color: Color(0xFF0F172A),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Usa este código en la entrada del gimnasio',
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _StatsCard extends StatelessWidget {
  final Map<String, dynamic>? stats;

  const _StatsCard({this.stats});

  @override
  Widget build(BuildContext context) {
    final monthlyVisits = stats?['monthly_visits'] ?? 0;
    final currentStreak = stats?['current_streak'] ?? 0;
    final totalVisits = stats?['total_visits'] ?? 0;

    return _InfoCard(
      children: [
        Row(
          children: [
            Expanded(
              child: _StatItem(
                icon: Icons.calendar_month,
                label: 'Este Mes',
                value: monthlyVisits.toString(),
                color: Colors.blue,
              ),
            ),
            Container(
              width: 1,
              height: 50,
              color: Colors.grey[200],
            ),
            Expanded(
              child: _StatItem(
                icon: Icons.local_fire_department,
                label: 'Racha',
                value: '$currentStreak días',
                color: Colors.orange,
              ),
            ),
          ],
        ),
        const Divider(height: 32),
        _StatItem(
          icon: Icons.fitness_center,
          label: 'Visitas Totales',
          value: totalVisits.toString(),
          color: Colors.green,
        ),
      ],
    );
  }
}

class _StatItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatItem({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 8),
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Color(0xFF0F172A),
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey[600],
          ),
        ),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_service.dart';
import '../widgets/promo_section.dart';
import 'gamification_screen.dart';
import 'referrals_screen.dart';
import 'wallet_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  bool _referralEnabled = false;
  Map<String, dynamic>? _walletBalance;
  bool _walletEnabled = false;

  @override
  void initState() {
    super.initState();
    _checkReferralStatus();
    _checkWalletStatus();
  }

  Future<void> _checkReferralStatus() async {
    final api = Provider.of<ApiService>(context, listen: false);
    try {
      final status = await api.getReferralStatus();
      if (mounted) {
        setState(() {
          _referralEnabled = status['enabled'] ?? false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _referralEnabled = false;
        });
      }
    }
  }

  Future<void> _checkWalletStatus() async {
    final api = Provider.of<ApiService>(context, listen: false);
    try {
      final balance = await api.getWalletBalance();
      if (mounted) {
        setState(() {
          _walletBalance = balance;
          _walletEnabled = balance['show'] == true;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _walletEnabled = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = Provider.of<ApiService>(context);
    final client = api.currentClient;

    if (client == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final brandColor = api.brandColor;
    final brandColorDark = api.brandColorDark;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: CustomScrollView(
        slivers: [
          // Header with profile picture
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            backgroundColor: brandColor,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [brandColor, brandColorDark],
                  ),
                ),
                child: SafeArea(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox(height: 20),
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
          ),

          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Personal Information Section
                  const _SectionTitle(title: 'Información Personal'),
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
                        value: client.phone.isNotEmpty ? client.phone : '--',
                      ),
                      const Divider(height: 24),
                      _InfoRow(
                        icon: Icons.badge_outlined,
                        label: 'DNI',
                        value: client.dni.isNotEmpty ? client.dni : '--',
                      ),
                      const Divider(height: 24),
                      _InfoRow(
                        icon: Icons.cake_outlined,
                        label: 'FECHA NACIMIENTO',
                        value: client.birthDate.isNotEmpty
                            ? client.birthDate
                            : '--',
                      ),
                      const Divider(height: 24),
                      _InfoRow(
                        icon: Icons.home_outlined,
                        label: 'DIRECCIÓN',
                        value:
                            client.address.isNotEmpty ? client.address : '--',
                      ),
                      if (client.clientType.isNotEmpty) ...[
                        const Divider(height: 24),
                        _InfoRow(
                          icon: Icons.person_outline,
                          label: 'TIPO DE CLIENTE',
                          value: client.clientType,
                        ),
                      ],
                    ],
                  ),

                  const SizedBox(height: 24),

                  // Membership Section
                  const _SectionTitle(title: 'Membresía'),
                  const SizedBox(height: 12),
                  _MembershipCard(membership: client.activeMembership),

                  const SizedBox(height: 24),

                  // Access Code Section
                  const _SectionTitle(title: 'Código de Acceso'),
                  const SizedBox(height: 12),
                  _AccessCodeCard(accessCode: client.accessCode),

                  const SizedBox(height: 24),

                  // Stats Section
                  const _SectionTitle(title: 'Estadísticas'),
                  const SizedBox(height: 12),
                  _StatsCard(stats: client.stats),

                  const SizedBox(height: 24),

                  // Promotional Advertisements
                  const PromoSection(
                    screen: 'PROFILE',
                    padding: EdgeInsets.symmetric(vertical: 8),
                  ),

                  const SizedBox(height: 24),

                  // Settings Section
                  const _SectionTitle(title: 'Configuración'),
                  const SizedBox(height: 12),
                  _InfoCard(
                    children: [
                      // Wallet - only show if enabled
                      if (_walletEnabled) ...[
                        _SettingsRow(
                          icon: Icons.account_balance_wallet,
                          iconColor: Colors.green,
                          label: 'Mi Monedero',
                          subtitle: _walletBalance != null 
                            ? 'Saldo: ${_walletBalance!['balance_display'] ?? '0.00€'}'
                            : 'Tu saldo de cuenta',
                          trailing: _walletBalance != null && (_walletBalance!['is_positive'] == true)
                            ? Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                decoration: BoxDecoration(
                                  color: Colors.green.shade100,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  _walletBalance!['balance_display'] ?? '',
                                  style: TextStyle(
                                    color: Colors.green.shade700,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              )
                            : null,
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const WalletScreen(),
                              ),
                            ).then((_) => _checkWalletStatus());
                          },
                        ),
                        const Divider(height: 24),
                      ],
                      _SettingsRow(
                        icon: Icons.emoji_events_outlined,
                        label: 'Gamificación',
                        subtitle: 'Logros, retos y ranking',
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) =>
                                  GamificationScreen(api: api),
                            ),
                          );
                        },
                      ),
                      // Referrals - only show if enabled
                      if (_referralEnabled) ...[
                        const Divider(height: 24),
                        _SettingsRow(
                          icon: Icons.card_giftcard_outlined,
                          label: 'Invitar Amigos',
                          subtitle: 'Comparte y gana recompensas',
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const ReferralsScreen(),
                              ),
                            );
                          },
                        ),
                      ],
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.chat_bubble_outline,
                        label: 'Chat con el Gimnasio',
                        onTap: () {
                          Navigator.pushNamed(context, '/chat');
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.lock_outline,
                        label: 'Cambiar Contraseña',
                        onTap: () {
                          _showChangePasswordDialog(context, api);
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.description_outlined,
                        label: 'Historial de Clases',
                        onTap: () {
                          Navigator.pushNamed(context, '/history');
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.receipt_long_outlined,
                        label: 'Facturación',
                        onTap: () {
                          Navigator.pushNamed(context, '/billing');
                        },
                      ),
                      const Divider(height: 24),
                      _SettingsRow(
                        icon: Icons.credit_card_outlined,
                        label: 'Método de Pago',
                        subtitle: 'Gestiona tu tarjeta bancaria',
                        onTap: () {
                          Navigator.pushNamed(context, '/payment-methods');
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
                            content: const Text(
                                '¿Estás seguro que deseas cerrar sesión?'),
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
                overflow: TextOverflow.ellipsis,
                maxLines: 1,
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFF0F172A),
                ),
                overflow: TextOverflow.ellipsis,
                maxLines: 3,
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
  final Color? iconColor;
  final String label;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback onTap;

  const _SettingsRow({
    required this.icon,
    this.iconColor,
    required this.label,
    this.subtitle,
    this.trailing,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveIconColor = iconColor ?? const Color(0xFF0F172A);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: effectiveIconColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 20, color: effectiveIconColor),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFF0F172A),
                  ),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey[600],
                    ),
                  ),
              ],
            ),
          ),
          if (trailing != null) ...[
            trailing!,
            const SizedBox(width: 8),
          ],
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
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
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
                const Icon(Icons.calendar_today,
                    color: Colors.white70, size: 16),
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

void _showChangePasswordDialog(BuildContext context, ApiService api) {
  final currentPasswordController = TextEditingController();
  final newPasswordController = TextEditingController();
  final confirmPasswordController = TextEditingController();
  bool isLoading = false;

  showDialog(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (context, setState) => AlertDialog(
        title: const Text('Cambiar Contraseña'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: currentPasswordController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Contraseña Actual',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: newPasswordController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Nueva Contraseña',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: confirmPasswordController,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Confirmar Nueva Contraseña',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: isLoading ? null : () => Navigator.pop(ctx),
            child: const Text('Cancelar'),
          ),
          ElevatedButton(
            onPressed: isLoading
                ? null
                : () async {
                    if (newPasswordController.text !=
                        confirmPasswordController.text) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                            content: Text('Las contraseñas no coinciden')),
                      );
                      return;
                    }
                    if (newPasswordController.text.length < 8) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                            content: Text(
                                'La contraseña debe tener al menos 8 caracteres')),
                      );
                      return;
                    }

                    setState(() => isLoading = true);

                    final result = await api.changePassword(
                      currentPasswordController.text,
                      newPasswordController.text,
                    );

                    setState(() => isLoading = false);

                    Navigator.pop(ctx);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(result['message'] ??
                              (result['success'] == true
                                  ? 'Contraseña cambiada exitosamente'
                                  : 'Error al cambiar contraseña')),
                          backgroundColor: result['success'] == true
                              ? Colors.green
                              : Colors.red,
                        ),
                      );
                    }
                  },
            child: isLoading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Cambiar'),
          ),
        ],
      ),
    ),
  );
}

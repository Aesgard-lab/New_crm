import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../api/api_service.dart';

class ReferralsScreen extends StatefulWidget {
  const ReferralsScreen({super.key});

  @override
  State<ReferralsScreen> createState() => _ReferralsScreenState();
}

class _ReferralsScreenState extends State<ReferralsScreen> {
  bool _isLoading = true;
  dynamic _shareData;
  dynamic _stats;
  List<dynamic> _history = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      
      // Load all data in parallel
      final results = await Future.wait([
        api.getReferralCode(),
        api.getReferralStats(),
        api.getReferralHistory(),
      ]);

      if (mounted) {
        setState(() {
          _shareData = results[0];
          _stats = results[1];
          _history = (results[2] as List<dynamic>?) ?? [];
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Error al cargar datos de referidos';
          _isLoading = false;
        });
      }
    }
  }

  void _copyCode() {
    if (_shareData?.code != null) {
      Clipboard.setData(ClipboardData(text: _shareData!.code));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('¡Código copiado!'),
          duration: Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _copyLink() {
    if (_shareData?.link != null) {
      Clipboard.setData(ClipboardData(text: _shareData!.link));
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('¡Link copiado!'),
          duration: Duration(seconds: 2),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  void _shareViaWhatsApp() async {
    if (_shareData == null) return;
    
    final message = '${_shareData!.shareMessage}\n\n'
        'Usa mi código: ${_shareData!.code}\n\n'
        'Regístrate aquí: ${_shareData!.link}';
    
    final url = 'https://wa.me/?text=${Uri.encodeComponent(message)}';
    
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    }
  }

  void _shareViaEmail() async {
    if (_shareData == null) return;
    
    final subject = '¡Únete a ${_shareData!.gymName}!';
    final body = '${_shareData!.shareMessage}\n\n'
        'Usa mi código: ${_shareData!.code}\n\n'
        'Regístrate aquí: ${_shareData!.link}';
    
    final url = 'mailto:?subject=${Uri.encodeComponent(subject)}&body=${Uri.encodeComponent(body)}';
    
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url));
    }
  }

  void _shareNative() {
    if (_shareData == null) return;
    
    final message = '${_shareData!.shareMessage}\n\n'
        'Usa mi código: ${_shareData!.code}\n\n'
        'Regístrate aquí: ${_shareData!.link}';
    
    Share.share(message, subject: '¡Únete a ${_shareData!.gymName}!');
  }

  @override
  Widget build(BuildContext context) {
    final api = Provider.of<ApiService>(context);
    final brandColor = api.brandColor;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: CustomScrollView(
        slivers: [
          // Header
          SliverAppBar(
            expandedHeight: 180,
            pinned: true,
            backgroundColor: brandColor,
            leading: IconButton(
              icon: const Icon(Icons.arrow_back, color: Colors.white),
              onPressed: () => Navigator.pop(context),
            ),
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [brandColor, api.brandColorDark],
                  ),
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.end,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Invitar Amigos',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Comparte tu código y gana recompensas',
                          style: TextStyle(
                            color: Colors.white70,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 12),
                        // Rewards badges
                        if (_shareData?.program != null) ...[
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              _buildRewardBadge(
                                '🎁 Tú ganas: ${_shareData!.program!.referrerReward}',
                              ),
                              _buildRewardBadge(
                                '👤 Tu amigo: ${_shareData!.program!.referredReward}',
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

          // Content
          SliverToBoxAdapter(
            child: _isLoading
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(40),
                      child: CircularProgressIndicator(),
                    ),
                  )
                : _error != null
                    ? _buildErrorWidget()
                    : _buildContent(brandColor),
          ),
        ],
      ),
    );
  }

  Widget _buildRewardBadge(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.amber.shade100,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        text,
        style: TextStyle(
          color: Colors.amber.shade900,
          fontWeight: FontWeight.w600,
          fontSize: 12,
        ),
      ),
    );
  }

  Widget _buildErrorWidget() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        children: [
          Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
          const SizedBox(height: 16),
          Text(_error!, style: const TextStyle(color: Colors.red)),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _loadData,
            child: const Text('Reintentar'),
          ),
        ],
      ),
    );
  }

  Widget _buildContent(Color brandColor) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Code Card
          _buildCodeCard(brandColor),
          const SizedBox(height: 16),
          
          // Stats Card
          _buildStatsCard(brandColor),
          const SizedBox(height: 16),
          
          // History Card
          if (_history.isNotEmpty) ...[
            _buildHistoryCard(brandColor),
            const SizedBox(height: 16),
          ],
          
          // How it works
          _buildHowItWorksCard(brandColor),
          const SizedBox(height: 80),
        ],
      ),
    );
  }

  Widget _buildCodeCard(Color brandColor) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(0, 0, 0, 0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.card_giftcard, color: Colors.amber.shade600),
                const SizedBox(width: 8),
                const Text(
                  'Tu Código Personal',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            
            // Code Box
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.grey.shade100, Colors.grey.shade50],
                ),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.grey.shade300,
                  width: 2,
                  style: BorderStyle.solid,
                ),
              ),
              child: Column(
                children: [
                  Text(
                    _shareData?.code ?? '---',
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 4,
                      color: brandColor,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Comparte este código con tus amigos',
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            
            // Share Buttons
            Row(
              children: [
                Expanded(
                  child: _buildShareButton(
                    icon: Icons.message,
                    label: 'WhatsApp',
                    color: const Color(0xFF25D366),
                    onTap: _shareViaWhatsApp,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildShareButton(
                    icon: Icons.email,
                    label: 'Email',
                    color: const Color(0xFF6366F1),
                    onTap: _shareViaEmail,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _buildShareButton(
                    icon: Icons.share,
                    label: 'Compartir',
                    color: Colors.grey.shade600,
                    outlined: true,
                    onTap: _shareNative,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            
            // Copy buttons
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _copyCode,
                    icon: const Icon(Icons.copy, size: 18),
                    label: const Text('Copiar Código'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _copyLink,
                    icon: const Icon(Icons.link, size: 18),
                    label: const Text('Copiar Link'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildShareButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
    bool outlined = false,
  }) {
    if (outlined) {
      return OutlinedButton(
        onPressed: onTap,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(vertical: 12),
          side: BorderSide(color: color),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 20),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(color: color, fontSize: 11),
            ),
          ],
        ),
      );
    }
    
    return ElevatedButton(
      onPressed: onTap,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        foregroundColor: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 12),
        elevation: 0,
      ),
      child: Column(
        children: [
          Icon(icon, size: 20),
          const SizedBox(height: 4),
          Text(label, style: const TextStyle(fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildStatsCard(Color brandColor) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(0, 0, 0, 0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Tus Estadísticas',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    value: '${_stats?.totalInvited ?? 0}',
                    label: 'Invitados',
                    brandColor: brandColor,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    value: '${_stats?.completed ?? 0}',
                    label: 'Completados',
                    brandColor: brandColor,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    value: '${_stats?.totalCreditEarned ?? "0"}€',
                    label: 'Crédito',
                    brandColor: brandColor,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem({
    required String value,
    required String label,
    required Color brandColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.symmetric(horizontal: 4),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: brandColor,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: Colors.grey.shade600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryCard(Color brandColor) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(0, 0, 0, 0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.all(20),
            child: Text(
              'Historial de Invitaciones',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
          ),
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _history.length,
            separatorBuilder: (_, __) => Divider(
              height: 1,
              color: Colors.grey.shade100,
            ),
            itemBuilder: (context, index) {
              final item = _history[index];
              return _buildHistoryItem(item, brandColor);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryItem(dynamic item, Color brandColor) {
    Color statusColor;
    Color statusTextColor;
    switch (item.status) {
      case 'PENDING':
        statusColor = Colors.amber;
        statusTextColor = Colors.amber.shade700;
        break;
      case 'REGISTERED':
        statusColor = Colors.blue;
        statusTextColor = Colors.blue.shade700;
        break;
      case 'COMPLETED':
      case 'REWARDED':
        statusColor = Colors.green;
        statusTextColor = Colors.green.shade700;
        break;
      default:
        statusColor = Colors.grey;
        statusTextColor = Colors.grey.shade700;
    }

    return ListTile(
      leading: CircleAvatar(
        backgroundColor: brandColor.withValues(alpha: 0.1),
        child: Icon(Icons.person, color: brandColor, size: 20),
      ),
      title: Text(
        item.referredName ?? 'Invitado',
        style: const TextStyle(fontWeight: FontWeight.w600),
      ),
      subtitle: Text(
        item.invitedAt != null
            ? _formatDate(item.invitedAt!)
            : '',
        style: TextStyle(
          fontSize: 12,
          color: Colors.grey.shade600,
        ),
      ),
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: statusColor.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          item.statusDisplay ?? '',
          style: TextStyle(
            color: statusTextColor,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }

  String _formatDate(String isoDate) {
    try {
      final date = DateTime.parse(isoDate);
      return '${date.day}/${date.month}/${date.year}';
    } catch (e) {
      return '';
    }
  }

  Widget _buildHowItWorksCard(Color brandColor) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color.fromRGBO(0, 0, 0, 0.05),
            blurRadius: 10,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '¿Cómo funciona?',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
            const SizedBox(height: 16),
            _buildStep(
              number: '1',
              title: 'Comparte tu código',
              description: 'Envía tu código personal o link a tus amigos',
              brandColor: brandColor,
            ),
            const SizedBox(height: 12),
            _buildStep(
              number: '2',
              title: 'Tu amigo se registra',
              description: 'Debe usar tu código al crear su cuenta',
              brandColor: brandColor,
            ),
            const SizedBox(height: 12),
            _buildStep(
              number: '3',
              title: '¡Ambos ganan!',
              description: 'Recibís las recompensas automáticamente',
              brandColor: brandColor,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStep({
    required String number,
    required String title,
    required String description,
    required Color brandColor,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: brandColor.withValues(alpha: 0.1),
            shape: BoxShape.circle,
          ),
          child: Center(
            child: Text(
              number,
              style: TextStyle(
                color: brandColor,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                description,
                style: TextStyle(
                  fontSize: 13,
                  color: Colors.grey.shade600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

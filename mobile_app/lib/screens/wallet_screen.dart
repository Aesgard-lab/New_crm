import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import '../api/api_service.dart';

class WalletScreen extends StatefulWidget {
  const WalletScreen({super.key});

  @override
  State<WalletScreen> createState() => _WalletScreenState();
}

class _WalletScreenState extends State<WalletScreen> {
  bool _isLoading = true;
  dynamic _walletStatus;
  List<dynamic> _transactions = [];
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
      
      final results = await Future.wait([
        api.getWalletStatus(),
        api.getWalletHistory(),
      ]);

      if (mounted) {
        setState(() {
          _walletStatus = results[0];
          _transactions = (results[1]['transactions'] as List<dynamic>?) ?? [];
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Error al cargar datos del monedero';
          _isLoading = false;
        });
      }
    }
  }

  void _showTopupDialog() {
    if (_walletStatus?['settings']?['allow_online_topup'] != true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('La recarga online no está habilitada'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    final presetAmounts = (_walletStatus?['settings']?['preset_amounts'] as List<dynamic>?)
        ?.cast<num>()
        .map((e) => e.toDouble())
        .toList() ?? [20.0, 50.0, 100.0, 200.0];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => _TopupBottomSheet(
        presetAmounts: presetAmounts,
        settings: _walletStatus?['settings'],
        onTopup: _processTopup,
      ),
    );
  }

  Future<void> _processTopup(double amount) async {
    Navigator.pop(context);
    
    setState(() => _isLoading = true);
    
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.topupWallet(amount);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result['message'] ?? '¡Recarga iniciada!'),
            behavior: SnackBarBehavior.floating,
            backgroundColor: Colors.green,
          ),
        );
        _loadData();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: $e'),
            behavior: SnackBarBehavior.floating,
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi Monedero'),
        centerTitle: true,
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _error != null
          ? _buildErrorState()
          : _walletStatus?['enabled'] != true || _walletStatus?['show_in_app'] != true
            ? _buildDisabledState()
            : _buildWalletContent(theme),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.grey),
          const SizedBox(height: 16),
          Text(_error!, style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _loadData,
            child: const Text('Reintentar'),
          ),
        ],
      ),
    );
  }

  Widget _buildDisabledState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.account_balance_wallet_outlined, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text(
            'El monedero no está disponible',
            style: TextStyle(color: Colors.grey, fontSize: 16),
          ),
        ],
      ),
    );
  }

  Widget _buildWalletContent(ThemeData theme) {
    final wallet = _walletStatus?['wallet'];
    final balance = double.tryParse(wallet?['balance']?.toString() ?? '0') ?? 0;
    final isNegative = wallet?['is_negative'] == true;
    
    return RefreshIndicator(
      onRefresh: _loadData,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Balance Card
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: isNegative 
                    ? [Colors.red.shade400, Colors.red.shade600]
                    : balance > 0
                      ? [Colors.green.shade400, Colors.green.shade600]
                      : [Colors.grey.shade400, Colors.grey.shade600],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: (isNegative ? Colors.red : Colors.green).withValues(alpha: 0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 6),
                  ),
                ],
              ),
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  const Text(
                    'Saldo Disponible',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    wallet?['balance_display'] ?? '0.00€',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 42,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (wallet?['allow_negative'] == true) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Disponible con crédito: ${wallet?['available_balance'] ?? '0.00'}€',
                      style: const TextStyle(
                        color: Colors.white70,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Stats Row
            Row(
              children: [
                Expanded(
                  child: _StatCard(
                    icon: Icons.arrow_upward,
                    label: 'Recargado',
                    value: '${wallet?['total_topups'] ?? '0.00'}€',
                    color: Colors.blue,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _StatCard(
                    icon: Icons.arrow_downward,
                    label: 'Gastado',
                    value: '${wallet?['total_spent'] ?? '0.00'}€',
                    color: Colors.purple,
                  ),
                ),
              ],
            ),
            
            const SizedBox(height: 24),
            
            // Topup Button
            if (_walletStatus?['settings']?['allow_online_topup'] == true)
              ElevatedButton.icon(
                onPressed: _showTopupDialog,
                icon: const Icon(Icons.add),
                label: const Text('Recargar Saldo'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            
            // Bonus info
            if (_walletStatus?['settings']?['topup_bonus_enabled'] == true) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.amber.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.amber.shade200),
                ),
                child: Row(
                  children: [
                    const Text('🎁', style: TextStyle(fontSize: 20)),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Recibe un ${_walletStatus?['settings']?['topup_bonus_percent']}% extra al recargar',
                        style: TextStyle(
                          color: Colors.amber.shade900,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            
            const SizedBox(height: 24),
            
            // Transactions List
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Últimos Movimientos',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (_transactions.isNotEmpty)
                  TextButton(
                    onPressed: () {
                      // TODO: Navigate to full history
                    },
                    child: const Text('Ver todo'),
                  ),
              ],
            ),
            const SizedBox(height: 12),
            
            if (_transactions.isEmpty)
              Container(
                padding: const EdgeInsets.all(32),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Column(
                  children: [
                    Icon(Icons.receipt_long, size: 48, color: Colors.grey),
                    SizedBox(height: 12),
                    Text(
                      'Sin movimientos todavía',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              )
            else
              ...(_transactions.take(10).map((tx) => _TransactionTile(transaction: tx))),
          ],
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  const _StatCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(height: 8),
          Text(
            label,
            style: TextStyle(
              color: Colors.grey.shade600,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: const TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
}

class _TransactionTile extends StatelessWidget {
  final dynamic transaction;

  const _TransactionTile({required this.transaction});

  @override
  Widget build(BuildContext context) {
    final isCredit = transaction['is_credit'] == true;
    final amount = transaction['amount']?.toString() ?? '0.00';
    final createdAt = DateTime.tryParse(transaction['created_at'] ?? '');
    
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: isCredit ? Colors.green.shade50 : Colors.red.shade50,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(
              child: Text(
                transaction['icon'] ?? '📝',
                style: const TextStyle(fontSize: 18),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  transaction['type_display'] ?? 'Transacción',
                  style: const TextStyle(fontWeight: FontWeight.w500),
                ),
                Text(
                  transaction['description'] ?? '',
                  style: TextStyle(
                    color: Colors.grey.shade600,
                    fontSize: 12,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (createdAt != null)
                  Text(
                    DateFormat('dd/MM/yyyy HH:mm').format(createdAt),
                    style: TextStyle(
                      color: Colors.grey.shade400,
                      fontSize: 11,
                    ),
                  ),
              ],
            ),
          ),
          Text(
            '${isCredit ? '+' : ''}$amount€',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              fontSize: 16,
              color: isCredit ? Colors.green : Colors.red,
            ),
          ),
        ],
      ),
    );
  }
}

class _TopupBottomSheet extends StatefulWidget {
  final List<double> presetAmounts;
  final dynamic settings;
  final Function(double) onTopup;

  const _TopupBottomSheet({
    required this.presetAmounts,
    required this.settings,
    required this.onTopup,
  });

  @override
  State<_TopupBottomSheet> createState() => _TopupBottomSheetState();
}

class _TopupBottomSheetState extends State<_TopupBottomSheet> {
  double? _selectedAmount;
  final _customController = TextEditingController();
  double _bonus = 0;

  @override
  void dispose() {
    _customController.dispose();
    super.dispose();
  }

  void _selectAmount(double amount) {
    setState(() {
      _selectedAmount = amount;
      _customController.clear();
      _calculateBonus(amount);
    });
  }

  void _onCustomAmountChanged(String value) {
    final amount = double.tryParse(value);
    setState(() {
      _selectedAmount = amount;
      _calculateBonus(amount ?? 0);
    });
  }

  void _calculateBonus(double amount) {
    if (widget.settings?['topup_bonus_enabled'] != true) {
      _bonus = 0;
      return;
    }
    
    final percent = double.tryParse(widget.settings?['topup_bonus_percent']?.toString() ?? '0') ?? 0;
    final minAmount = double.tryParse(widget.settings?['topup_bonus_min_amount']?.toString() ?? '0') ?? 0;
    
    if (amount >= minAmount) {
      _bonus = amount * (percent / 100);
    } else {
      _bonus = 0;
    }
  }

  @override
  Widget build(BuildContext context) {
    final minTopup = double.tryParse(widget.settings?['min_topup']?.toString() ?? '10') ?? 10;
    final maxTopup = double.tryParse(widget.settings?['max_topup']?.toString() ?? '500') ?? 500;

    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Recargar Saldo',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 20),
          
          // Preset amounts
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: widget.presetAmounts.map((amount) {
              final isSelected = _selectedAmount == amount;
              return ChoiceChip(
                label: Text('${amount.toStringAsFixed(0)}€'),
                selected: isSelected,
                onSelected: (_) => _selectAmount(amount),
                selectedColor: Theme.of(context).primaryColor.withValues(alpha: 0.2),
              );
            }).toList(),
          ),
          
          const SizedBox(height: 16),
          
          // Custom amount
          TextField(
            controller: _customController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              labelText: 'Otra cantidad',
              hintText: 'Introduce una cantidad',
              prefixText: '€ ',
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              helperText: 'Mínimo: ${minTopup.toStringAsFixed(0)}€ - Máximo: ${maxTopup.toStringAsFixed(0)}€',
            ),
            onChanged: _onCustomAmountChanged,
          ),
          
          // Bonus preview
          if (_bonus > 0) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                children: [
                  const Text('🎁', style: TextStyle(fontSize: 20)),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          '¡Recibirás bonus!',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                        Text(
                          'Recarga: ${_selectedAmount?.toStringAsFixed(2)}€ + Bonus: ${_bonus.toStringAsFixed(2)}€ = ${((_selectedAmount ?? 0) + _bonus).toStringAsFixed(2)}€',
                          style: TextStyle(
                            color: Colors.green.shade700,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
          
          const SizedBox(height: 24),
          
          // Confirm button
          ElevatedButton(
            onPressed: _selectedAmount != null && 
                       _selectedAmount! >= minTopup && 
                       _selectedAmount! <= maxTopup
              ? () => widget.onTopup(_selectedAmount!)
              : null,
            style: ElevatedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: Text(
              _selectedAmount != null 
                ? 'Recargar ${_selectedAmount!.toStringAsFixed(2)}€'
                : 'Selecciona una cantidad',
              style: const TextStyle(fontSize: 16),
            ),
          ),
        ],
      ),
    );
  }
}

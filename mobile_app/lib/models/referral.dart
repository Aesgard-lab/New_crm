/// Modelos para el sistema de referidos

class ReferralProgram {
  final String name;
  final String description;
  final String referrerReward;
  final String referredReward;

  ReferralProgram({
    required this.name,
    required this.description,
    required this.referrerReward,
    required this.referredReward,
  });

  factory ReferralProgram.fromJson(Map<String, dynamic> json) {
    return ReferralProgram(
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      referrerReward: json['referrer_reward'] ?? '',
      referredReward: json['referred_reward'] ?? '',
    );
  }
}

class ReferralShareData {
  final String code;
  final String link;
  final String shareMessage;
  final String gymName;
  final ReferralProgram? program;

  ReferralShareData({
    required this.code,
    required this.link,
    required this.shareMessage,
    required this.gymName,
    this.program,
  });

  factory ReferralShareData.fromJson(Map<String, dynamic> json) {
    return ReferralShareData(
      code: json['code'] ?? '',
      link: json['link'] ?? '',
      shareMessage: json['share_message'] ?? '',
      gymName: json['gym_name'] ?? '',
      program: json['program'] != null 
          ? ReferralProgram.fromJson(json['program']) 
          : null,
    );
  }
}

class ReferralStats {
  final int totalInvited;
  final int pending;
  final int registered;
  final int completed;
  final String totalCreditEarned;

  ReferralStats({
    required this.totalInvited,
    required this.pending,
    required this.registered,
    required this.completed,
    required this.totalCreditEarned,
  });

  factory ReferralStats.fromJson(Map<String, dynamic> json) {
    return ReferralStats(
      totalInvited: json['total_invited'] ?? 0,
      pending: json['pending'] ?? 0,
      registered: json['registered'] ?? 0,
      completed: json['completed'] ?? 0,
      totalCreditEarned: json['total_credit_earned']?.toString() ?? '0.00',
    );
  }
}

class ReferralHistory {
  final int id;
  final String referredName;
  final String status;
  final String statusDisplay;
  final String? invitedAt;
  final String? registeredAt;
  final String? completedAt;
  final String creditEarned;

  ReferralHistory({
    required this.id,
    required this.referredName,
    required this.status,
    required this.statusDisplay,
    this.invitedAt,
    this.registeredAt,
    this.completedAt,
    required this.creditEarned,
  });

  factory ReferralHistory.fromJson(Map<String, dynamic> json) {
    return ReferralHistory(
      id: json['id'] ?? 0,
      referredName: json['referred_name'] ?? 'Invitado',
      status: json['status'] ?? 'PENDING',
      statusDisplay: json['status_display'] ?? 'Pendiente',
      invitedAt: json['invited_at'],
      registeredAt: json['registered_at'],
      completedAt: json['completed_at'],
      creditEarned: json['credit_earned']?.toString() ?? '0.00',
    );
  }
}

class ReferralStatus {
  final bool enabled;
  final ReferralProgram? program;

  ReferralStatus({
    required this.enabled,
    this.program,
  });

  factory ReferralStatus.fromJson(Map<String, dynamic> json) {
    return ReferralStatus(
      enabled: json['enabled'] ?? false,
      program: json['program'] != null 
          ? ReferralProgram.fromJson(json['program']) 
          : null,
    );
  }
}

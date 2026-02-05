// Models for Schedule and Bookings

class Activity {
  final int id;
  final String name;
  final String description;
  final String color;
  final String icon;

  Activity({
    required this.id,
    required this.name,
    required this.description,
    required this.color,
    required this.icon,
  });

  factory Activity.fromJson(Map<String, dynamic> json) {
    return Activity(
      id: json['id'],
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      color: json['color'] ?? '#000000',
      icon: json['icon'] ?? '',
    );
  }
}

class Instructor {
  final int id;
  final String fullName;
  final String email;

  Instructor({
    required this.id,
    required this.fullName,
    required this.email,
  });

  factory Instructor.fromJson(Map<String, dynamic> json) {
    return Instructor(
      id: json['id'],
      fullName: json['full_name'] ?? '',
      email: json['email'] ?? '',
    );
  }
}

class WaitlistInfo {
  final bool enabled;
  final String? mode;
  final bool isInWaitlist;
  final int? waitlistPosition;
  final int? waitlistEntryId;
  final String? waitlistStatus;
  final bool canClaim;
  final DateTime? claimExpiresAt;
  final int waitlistCount;

  WaitlistInfo({
    required this.enabled,
    this.mode,
    required this.isInWaitlist,
    this.waitlistPosition,
    this.waitlistEntryId,
    this.waitlistStatus,
    required this.canClaim,
    this.claimExpiresAt,
    required this.waitlistCount,
  });

  factory WaitlistInfo.fromJson(Map<String, dynamic> json) {
    return WaitlistInfo(
      enabled: json['enabled'] ?? false,
      mode: json['mode'],
      isInWaitlist: json['is_in_waitlist'] ?? false,
      waitlistPosition: json['waitlist_position'],
      waitlistEntryId: json['waitlist_entry_id'],
      waitlistStatus: json['waitlist_status'],
      canClaim: json['can_claim'] ?? false,
      claimExpiresAt: json['claim_expires_at'] != null
          ? DateTime.parse(json['claim_expires_at'])
          : null,
      waitlistCount: json['waitlist_count'] ?? 0,
    );
  }
}

class ActivitySession {
  final int id;
  final Activity activity;
  final Instructor? instructor;
  final DateTime startDatetime;
  final DateTime endDatetime;
  final int maxCapacity;
  final int availableSpots;
  final bool isBooked;
  final String location;
  final WaitlistInfo waitlistInfo;

  ActivitySession({
    required this.id,
    required this.activity,
    this.instructor,
    required this.startDatetime,
    required this.endDatetime,
    required this.maxCapacity,
    required this.availableSpots,
    required this.isBooked,
    required this.location,
    required this.waitlistInfo,
  });

  factory ActivitySession.fromJson(Map<String, dynamic> json) {
    return ActivitySession(
      id: json['id'],
      activity: Activity.fromJson(json['activity']),
      instructor: json['instructor'] != null 
          ? Instructor.fromJson(json['instructor'])
          : null,
      startDatetime: DateTime.parse(json['start_datetime']),
      endDatetime: DateTime.parse(json['end_datetime']),
      maxCapacity: json['max_capacity'] ?? 0,
      availableSpots: json['available_spots'] ?? 0,
      isBooked: json['is_booked'] ?? false,
      location: json['location'] ?? '',
      waitlistInfo: json['waitlist_info'] != null
          ? WaitlistInfo.fromJson(json['waitlist_info'])
          : WaitlistInfo(enabled: false, isInWaitlist: false, canClaim: false, waitlistCount: 0),
    );
  }

  bool get isFull => availableSpots == 0;
  
  String get timeRange {
    final start = '${startDatetime.hour.toString().padLeft(2, '0')}:${startDatetime.minute.toString().padLeft(2, '0')}';
    final end = '${endDatetime.hour.toString().padLeft(2, '0')}:${endDatetime.minute.toString().padLeft(2, '0')}';
    return '$start - $end';
  }
  
  String get dateString {
    final months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    return '${startDatetime.day} ${months[startDatetime.month - 1]}';
  }
}

class Booking {
  final int id;
  final ActivitySession session;
  final String activityName;
  final String? instructorName;
  final String status;
  final DateTime bookedAt;
  final bool attended;

  Booking({
    required this.id,
    required this.session,
    required this.activityName,
    this.instructorName,
    required this.status,
    required this.bookedAt,
    required this.attended,
  });

  factory Booking.fromJson(Map<String, dynamic> json) {
    return Booking(
      id: json['id'],
      session: ActivitySession.fromJson(json['session']),
      activityName: json['activity_name'] ?? '',
      instructorName: json['instructor_name'],
      status: json['status'] ?? '',
      bookedAt: DateTime.parse(json['booked_at']),
      attended: json['attended'] ?? false,
    );
  }

  bool get isConfirmed => status == 'CONFIRMED';
  bool get isCancelled => status == 'CANCELLED';
}

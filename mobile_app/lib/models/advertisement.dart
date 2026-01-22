class Advertisement {
  final int id;
  final String title;
  final String position;
  final String adType;
  final String imageDesktop;
  final String? imageMobile;
  final String? videoUrl;
  final String? ctaText;
  final String? ctaAction;
  final String? ctaUrl;
  final List<String> targetScreens;
  final int priority;
  final int durationSeconds;
  final bool isCollapsible;

  Advertisement({
    required this.id,
    required this.title,
    required this.position,
    required this.adType,
    required this.imageDesktop,
    this.imageMobile,
    this.videoUrl,
    this.ctaText,
    this.ctaAction,
    this.ctaUrl,
    required this.targetScreens,
    required this.priority,
    required this.durationSeconds,
    required this.isCollapsible,
  });

  factory Advertisement.fromJson(Map<String, dynamic> json) {
    return Advertisement(
      id: json['id'],
      title: json['title'] ?? '',
      position: json['position'] ?? '',
      adType: json['ad_type'] ?? '',
      imageDesktop: json['image_desktop'] ?? '',
      imageMobile: json['image_mobile'],
      videoUrl: json['video_url'],
      ctaText: json['cta_text'],
      ctaAction: json['cta_action'],
      ctaUrl: json['cta_url'],
      targetScreens: List<String>.from(json['target_screens'] ?? []),
      priority: json['priority'] ?? 1,
      durationSeconds: json['duration_seconds'] ?? 5,
      isCollapsible: json['is_collapsible'] ?? true,
    );
  }

  String get displayImage => imageMobile ?? imageDesktop;

  bool get hasCta => ctaText != null && ctaText!.isNotEmpty;
}

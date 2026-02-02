import 'package:flutter/material.dart';
// ignore: avoid_web_libraries_in_flutter
import 'dart:html' as html;
// ignore: undefined_prefixed_name
import 'dart:ui_web' as ui_web;

class YoutubePlayerWeb extends StatefulWidget {
  final String embedUrl;
  final double? height;
  final double? width;

  const YoutubePlayerWeb({
    super.key,
    required this.embedUrl,
    this.height,
    this.width,
  });

  @override
  State<YoutubePlayerWeb> createState() => _YoutubePlayerWebState();
}

class _YoutubePlayerWebState extends State<YoutubePlayerWeb> {
  late String _viewId;
  bool _registered = false;

  @override
  void initState() {
    super.initState();
    _viewId = 'youtube-player-${DateTime.now().millisecondsSinceEpoch}';
    _registerViewFactory();
  }

  void _registerViewFactory() {
    // ignore: undefined_prefixed_name
    ui_web.platformViewRegistry.registerViewFactory(
      _viewId,
      (int viewId) => html.IFrameElement()
        ..src = widget.embedUrl
        ..style.border = 'none'
        ..style.width = '100%'
        ..style.height = '100%'
        ..allowFullscreen = true
        ..allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture',
    );
    _registered = true;
  }

  @override
  Widget build(BuildContext context) {
    if (!_registered) {
      return const Center(child: CircularProgressIndicator());
    }

    return SizedBox(
      height: widget.height,
      width: widget.width,
      child: HtmlElementView(viewType: _viewId),
    );
  }
}

/// Helper function to extract YouTube video ID from various URL formats
String? extractYoutubeVideoId(String? url) {
  if (url == null || url.isEmpty) return null;

  // YouTube watch URL: youtube.com/watch?v=VIDEO_ID
  final watchMatch = RegExp(r'[?&]v=([^&]+)').firstMatch(url);
  if (watchMatch != null) {
    return watchMatch.group(1);
  }

  // YouTube short URL: youtu.be/VIDEO_ID
  if (url.contains('youtu.be/')) {
    return url.split('youtu.be/')[1].split('?')[0];
  }

  // YouTube embed URL: youtube.com/embed/VIDEO_ID
  if (url.contains('/embed/')) {
    return url.split('/embed/')[1].split('?')[0];
  }

  return null;
}

/// Get embed URL from video URL
String? getEmbedUrl(String? url) {
  if (url == null || url.isEmpty) return null;

  final videoId = extractYoutubeVideoId(url);
  if (videoId != null && videoId.isNotEmpty) {
    return 'https://www.youtube.com/embed/$videoId?rel=0&modestbranding=1';
  }

  // Vimeo
  final vimeoMatch = RegExp(r'vimeo\.com/(\d+)').firstMatch(url);
  if (vimeoMatch != null) {
    return 'https://player.vimeo.com/video/${vimeoMatch.group(1)}';
  }

  return url;
}

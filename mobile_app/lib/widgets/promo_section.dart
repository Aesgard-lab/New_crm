import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/advertisement.dart';
import '../api/api_service.dart';
import 'promo_card.dart';

class PromoSection extends StatefulWidget {
  final String screen;
  final String? position;
  final String? title;
  final EdgeInsets? padding;

  const PromoSection({
    super.key,
    required this.screen,
    this.position,
    this.title,
    this.padding,
  });

  @override
  State<PromoSection> createState() => _PromoSectionState();
}

class _PromoSectionState extends State<PromoSection> {
  List<Advertisement> _ads = [];
  bool _isLoading = true;
  bool _impressionsTracked = false;

  @override
  void initState() {
    super.initState();
    _loadAdvertisements();
  }

  Future<void> _loadAdvertisements() async {
    // TODO: Temporarily disabled - fix API methods
    setState(() {
      _ads = [];
      _isLoading = false;
    });
    return;
    
    /*
    final api = Provider.of<ApiService>(context, listen: false);

    setState(() => _isLoading = true);

    final ads = await api.getAdvertisements(
      screen: widget.screen,
      position: widget.position,
    );

    setState(() {
      _ads = ads;
      _isLoading = false;
    });

    // Track impressions for all loaded ads
    if (!_impressionsTracked && ads.isNotEmpty) {
      _impressionsTracked = true;
      for (final ad in ads) {
        api.trackAdvertisementImpression(ad.id);
      }
    }
    */
  }

  void _handleAdTap(Advertisement ad) {
    // Handle different CTA actions
    switch (ad.ctaAction) {
      case 'BOOK_CLASS':
        // Navigate to class booking
        print('Navigate to book class: ${ad.ctaUrl}');
        break;
      case 'VIEW_CATALOG':
        // Navigate to catalog
        print('Navigate to catalog');
        break;
      case 'EXTERNAL_URL':
        // Open external URL
        print('Open URL: ${ad.ctaUrl}');
        break;
      case 'VIEW_PROMO':
        // Show promo details
        print('Show promo: ${ad.ctaUrl}');
        break;
      default:
        print('No action defined');
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Container(
        height: 200,
        padding: widget.padding ?? const EdgeInsets.symmetric(vertical: 16),
        child: const Center(
          child: CircularProgressIndicator(
            strokeWidth: 2,
            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF0F172A)),
          ),
        ),
      );
    }

    if (_ads.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      padding: widget.padding ?? const EdgeInsets.symmetric(vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Section Title
          if (widget.title != null)
            Padding(
              padding: const EdgeInsets.only(left: 20, bottom: 12),
              child: Text(
                widget.title!,
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF0F172A),
                ),
              ),
            ),

          // Horizontal Scrolling Cards
          SizedBox(
            height: 180,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              itemCount: _ads.length,
              itemBuilder: (context, index) {
                final ad = _ads[index];
                return PromoCard(
                  ad: ad,
                  onTap: () => _handleAdTap(ad),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

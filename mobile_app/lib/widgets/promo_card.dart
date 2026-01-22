import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/advertisement.dart';
import '../api/api_service.dart';

class PromoCard extends StatelessWidget {
  final Advertisement ad;
  final VoidCallback? onTap;

  const PromoCard({
    super.key,
    required this.ad,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    // TODO: Temporarily disabled tracking
    // final api = Provider.of<ApiService>(context, listen: false);

    return GestureDetector(
      onTap: () {
        // Track click - temporarily disabled
        // api.trackAdvertisementClick(ad.id);
        
        // Handle CTA action
        if (ad.hasCta && onTap != null) {
          onTap!();
        }
      },
      child: Container(
        width: 320,
        margin: const EdgeInsets.only(right: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Stack(
            children: [
              // Image
              Image.network(
                ad.displayImage,
                width: 320,
                height: 180,
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) {
                  return Container(
                    width: 320,
                    height: 180,
                    color: Colors.grey[200],
                    child: const Icon(Icons.image_not_supported, size: 48, color: Colors.grey),
                  );
                },
              ),

              // Gradient overlay
              Positioned.fill(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        Colors.transparent,
                        Colors.black.withOpacity(0.6),
                      ],
                    ),
                  ),
                ),
              ),

              // CTA Button
              if (ad.hasCta)
                Positioned(
                  bottom: 16,
                  left: 16,
                  right: 16,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.1),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          ad.ctaText!,
                          style: const TextStyle(
                            color: Color(0xFF0F172A),
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 8),
                        const Icon(
                          Icons.arrow_forward,
                          color: Color(0xFF0F172A),
                          size: 18,
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

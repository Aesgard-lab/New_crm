import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'screens/splash_screen.dart';
import 'screens/gym_search_screen.dart';
import 'screens/login_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/history_screen.dart';
import 'screens/billing_screen.dart';
import 'screens/payment_methods_screen.dart';
import 'widgets/main_navigator.dart';
import 'api/api_service.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ApiService()),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Gym Portal',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0F172A)),
        useMaterial3: true,
        textTheme: GoogleFonts.outfitTextTheme(),
      ),
      initialRoute: '/',
      routes: {
        '/': (context) => const SplashScreen(),
        '/search': (context) => const GymSearchScreen(),
        '/login': (context) => const LoginScreen(),
        '/home': (context) => const MainNavigator(),
        '/chat': (context) => const ChatScreen(),
        '/history': (context) => const HistoryScreen(),
        '/billing': (context) => const BillingScreen(),
        '/payment-methods': (context) => const PaymentMethodsScreen(),
      },
    );
  }
}

from django.urls import path
from . import views
from .password_reset_views import PasswordResetRequestView, PasswordResetConfirmView
from .registration_views import RegistrationConfigView, RegisterClientView
from .schedule_views import (
    ScheduleView,
    ActivitiesView,
    BookSessionView,
    CancelBookingView,
    MyBookingsView,
    FranchiseGymsView,
    JoinWaitlistView,
    LeaveWaitlistView,
    ClaimWaitlistSpotView,
    MyWaitlistEntriesView,
    SessionSpotsView
)
from .routine_views import (
    ClientRoutinesListView,
    RoutineDetailView,
    ExerciseDetailView
)
from .workout_views import (
    StartWorkoutView,
    WorkoutStatusView,
    LogSetView,
    CompleteExerciseView,
    FinishWorkoutView,
    WorkoutHistoryView,
    ActiveWorkoutView
)
from .checkin_views import (
    GenerateQRTokenView,
    RefreshQRTokenView,
    CheckinHistoryView,
    TodaysSessionsView,
    QuickCheckinView
)
from .profile_views import (
    ProfileView,
    ChangePasswordView,
    ToggleNotificationsView,
    MembershipDetailView,
    PaymentMethodsView,
    PaymentMethodDetailView
)
from .shop_views import (
    ShopView,
    RequestInfoView,
    ScheduleMembershipChangeView
)
from .document_views import (
    DocumentListView,
    DocumentDetailView,
    SignDocumentView
)
from .chat_views import (
    ChatRoomView,
    ChatMessagesView,
    MarkReadView
)
from .notification_views import (
    PopupNotificationsView,
    DismissPopupView
)
from .billing_views import BillingHistoryView
from .history_views import ClassHistoryView, SubmitReviewView
from .gamification_views import (
    GamificationStatusView,
    LeaderboardView,
    AchievementsView,
    ChallengesView,
    JoinChallengeView,
    XPHistoryView
)
from .advance_payment_api import advance_payment_info, process_advance_payment
from .calendar_views import (
    CalendarSettingsView,
    RegenerateCalendarTokenView,
    DownloadBookingICSView,
    AddToCalendarView
)
from .referral_views import (
    ReferralStatusView,
    ReferralCodeView,
    ReferralStatsView,
    ReferralHistoryView,
    ValidateReferralCodeView,
    InviteFriendView
)
from .wallet_views import (
    WalletStatusView,
    WalletBalanceView,
    WalletHistoryView,
    WalletTopupView,
    WalletBonusCalculatorView
)

urlpatterns = [
    # System Config
    path('system/config/', views.SystemConfigView.as_view(), name='api_system_config'),
    
    # Authentication & Registration
    path('gyms/search/', views.GymSearchView.as_view(), name='api_gym_search'),
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/check/', views.CheckAuthView.as_view(), name='api_check_auth'),
    path('registration/config/', RegistrationConfigView.as_view(), name='api_registration_config'),
    path('registration/register/', RegisterClientView.as_view(), name='api_register_client'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='api_password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='api_password_reset_confirm'),
    
    # Schedule & Bookings
    path('schedule/', ScheduleView.as_view(), name='api_schedule'),
    path('activities/', ActivitiesView.as_view(), name='api_activities'),
    path('bookings/book/', BookSessionView.as_view(), name='api_book_session'),
    path('bookings/<int:booking_id>/cancel/', CancelBookingView.as_view(), name='api_cancel_booking'),
    path('bookings/session/<int:session_id>/spots/', SessionSpotsView.as_view(), name='api_session_spots'),
    path('bookings/my-bookings/', MyBookingsView.as_view(), name='api_my_bookings'),
    path('franchise/gyms/', FranchiseGymsView.as_view(), name='api_franchise_gyms'),
    
    # Waitlist
    path('waitlist/join/', JoinWaitlistView.as_view(), name='api_waitlist_join'),
    path('waitlist/<int:entry_id>/leave/', LeaveWaitlistView.as_view(), name='api_waitlist_leave'),
    path('waitlist/<int:entry_id>/claim/', ClaimWaitlistSpotView.as_view(), name='api_waitlist_claim'),
    path('waitlist/my-entries/', MyWaitlistEntriesView.as_view(), name='api_waitlist_my_entries'),
    
    # Routines (Mobile App)
    path('routines/', ClientRoutinesListView.as_view(), name='api_client_routines'),
    path('routines/<int:routine_id>/', RoutineDetailView.as_view(), name='api_routine_detail'),
    path('exercises/<int:exercise_id>/', ExerciseDetailView.as_view(), name='api_exercise_detail'),
    
    # Workout Tracking (Mobile App)
    path('workout/start/', StartWorkoutView.as_view(), name='api_workout_start'),
    path('workout/active/', ActiveWorkoutView.as_view(), name='api_workout_active'),
    path('workout/history/', WorkoutHistoryView.as_view(), name='api_workout_history'),
    path('workout/<int:workout_id>/', WorkoutStatusView.as_view(), name='api_workout_status'),
    path('workout/<int:workout_id>/log/<int:exercise_log_id>/set/', LogSetView.as_view(), name='api_workout_log_set'),
    path('workout/<int:workout_id>/log/<int:exercise_log_id>/complete/', CompleteExerciseView.as_view(), name='api_workout_complete_exercise'),
    path('workout/<int:workout_id>/finish/', FinishWorkoutView.as_view(), name='api_workout_finish'),
    
    # Check-in QR (Mobile App)
    path('checkin/generate/', GenerateQRTokenView.as_view(), name='api_checkin_generate'),
    path('checkin/refresh/', RefreshQRTokenView.as_view(), name='api_checkin_refresh'),
    path('checkin/history/', CheckinHistoryView.as_view(), name='api_checkin_history'),
    path('checkin/todays-sessions/', TodaysSessionsView.as_view(), name='api_checkin_todays_sessions'),
    path('checkin/quick/', QuickCheckinView.as_view(), name='api_checkin_quick'),
    
    # Profile (Mobile App)
    path('profile/', ProfileView.as_view(), name='api_profile'),
    path('profile/change-password/', ChangePasswordView.as_view(), name='api_change_password'),
    path('profile/notifications/', ToggleNotificationsView.as_view(), name='api_toggle_notifications'),
    path('profile/membership/', MembershipDetailView.as_view(), name='api_membership_detail'),
    path('profile/payment-methods/', PaymentMethodsView.as_view(), name='api_payment_methods'),
    path('profile/payment-methods/<int:method_id>/', PaymentMethodDetailView.as_view(), name='api_payment_method_detail'),
    
    # Shop (Mobile App)
    path('shop/', ShopView.as_view(), name='api_shop'),
    path('shop/request-info/', RequestInfoView.as_view(), name='api_shop_request_info'),
    path('shop/schedule-change/', ScheduleMembershipChangeView.as_view(), name='api_shop_schedule_change'),
    
    # Documents (Mobile App)
    path('documents/', DocumentListView.as_view(), name='api_documents_list'),
    path('documents/<int:document_id>/', DocumentDetailView.as_view(), name='api_document_detail'),
    path('documents/<int:document_id>/sign/', SignDocumentView.as_view(), name='api_document_sign'),
    
    # Chat (Mobile App)
    path('chat/room/', ChatRoomView.as_view(), name='api_chat_room'),
    path('chat/messages/', ChatMessagesView.as_view(), name='api_chat_messages'),
    path('chat/read/', MarkReadView.as_view(), name='api_chat_read'),
    
    # Notifications (Mobile App)
    path('notifications/popup/', PopupNotificationsView.as_view(), name='api_notifications_popup'),
    path('notifications/popup/<int:note_id>/dismiss/', DismissPopupView.as_view(), name='api_notifications_dismiss'),
    
    # Billing (Mobile App)
    path('billing/history/', BillingHistoryView.as_view(), name='api_billing_history'),
    
    # Advance Payment (Mobile App)
    path('advance-payment/info/', advance_payment_info, name='api_advance_payment_info'),
    path('advance-payment/process/', process_advance_payment, name='api_advance_payment_process'),
    
    # History & Reviews (Mobile App)
    path('history/classes/', ClassHistoryView.as_view(), name='api_class_history'),
    path('history/reviews/', SubmitReviewView.as_view(), name='api_submit_review'),
    
    # Gamification (Mobile App)
    path('gamification/', GamificationStatusView.as_view(), name='api_gamification_status'),
    path('gamification/leaderboard/', LeaderboardView.as_view(), name='api_gamification_leaderboard'),
    path('gamification/achievements/', AchievementsView.as_view(), name='api_gamification_achievements'),
    path('gamification/challenges/', ChallengesView.as_view(), name='api_gamification_challenges'),
    path('gamification/challenges/<int:challenge_id>/join/', JoinChallengeView.as_view(), name='api_gamification_join_challenge'),
    path('gamification/xp-history/', XPHistoryView.as_view(), name='api_gamification_xp_history'),
    
    # Calendar Sync (Mobile App)
    path('calendar/settings/', CalendarSettingsView.as_view(), name='api_calendar_settings'),
    path('calendar/regenerate-token/', RegenerateCalendarTokenView.as_view(), name='api_calendar_regenerate'),
    path('calendar/booking/<int:booking_id>/ics/', DownloadBookingICSView.as_view(), name='api_calendar_booking_ics'),
    path('calendar/add-event/', AddToCalendarView.as_view(), name='api_calendar_add_event'),
    
    # Referral Program (Mobile App)
    path('referrals/status/', ReferralStatusView.as_view(), name='api_referral_status'),
    path('referrals/code/', ReferralCodeView.as_view(), name='api_referral_code'),
    path('referrals/stats/', ReferralStatsView.as_view(), name='api_referral_stats'),
    path('referrals/history/', ReferralHistoryView.as_view(), name='api_referral_history'),
    path('referrals/validate/', ValidateReferralCodeView.as_view(), name='api_referral_validate'),
    path('referrals/invite/', InviteFriendView.as_view(), name='api_referral_invite'),
    
    # Wallet / Monedero (Mobile App)
    path('wallet/status/', WalletStatusView.as_view(), name='api_wallet_status'),
    path('wallet/balance/', WalletBalanceView.as_view(), name='api_wallet_balance'),
    path('wallet/history/', WalletHistoryView.as_view(), name='api_wallet_history'),
    path('wallet/topup/', WalletTopupView.as_view(), name='api_wallet_topup'),
    path('wallet/bonus-calculator/', WalletBonusCalculatorView.as_view(), name='api_wallet_bonus'),
]








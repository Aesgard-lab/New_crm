from django.urls import path
from . import views
from .password_reset_views import PasswordResetRequestView, PasswordResetConfirmView
from .schedule_views import (
    ScheduleView,
    ActivitiesView,
    BookSessionView,
    CancelBookingView,
    MyBookingsView,
    FranchiseGymsView
)
from .routine_views import (
    ClientRoutinesListView,
    RoutineDetailView,
    ExerciseDetailView
)
from .checkin_views import (
    GenerateQRTokenView,
    RefreshQRTokenView,
    CheckinHistoryView
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
    RequestInfoView
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

urlpatterns = [
    # Authentication
    path('gyms/search/', views.GymSearchView.as_view(), name='api_gym_search'),
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/check/', views.CheckAuthView.as_view(), name='api_check_auth'),
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='api_password_reset_request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='api_password_reset_confirm'),
    
    # Schedule & Bookings
    path('schedule/', ScheduleView.as_view(), name='api_schedule'),
    path('activities/', ActivitiesView.as_view(), name='api_activities'),
    path('bookings/book/', BookSessionView.as_view(), name='api_book_session'),
    path('bookings/<int:booking_id>/cancel/', CancelBookingView.as_view(), name='api_cancel_booking'),
    path('bookings/my-bookings/', MyBookingsView.as_view(), name='api_my_bookings'),
    path('franchise/gyms/', FranchiseGymsView.as_view(), name='api_franchise_gyms'),
    
    # Routines (Mobile App)
    path('routines/', ClientRoutinesListView.as_view(), name='api_client_routines'),
    path('routines/<int:routine_id>/', RoutineDetailView.as_view(), name='api_routine_detail'),
    path('exercises/<int:exercise_id>/', ExerciseDetailView.as_view(), name='api_exercise_detail'),
    
    # Check-in QR (Mobile App)
    path('checkin/generate/', GenerateQRTokenView.as_view(), name='api_checkin_generate'),
    path('checkin/refresh/', RefreshQRTokenView.as_view(), name='api_checkin_refresh'),
    path('checkin/history/', CheckinHistoryView.as_view(), name='api_checkin_history'),
    
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
]








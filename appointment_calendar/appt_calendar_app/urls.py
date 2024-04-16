from django.urls import path,include, re_path
from . import views
from django.contrib.auth.views import LogoutView
from appointment_calendar import settings

urlpatterns = [    
    path('appointment_wizard/<int:business_id>', views.BookingCreateWizardView.as_view(), name='appointment_wizard'),
    path('cancel_appointment/<pk>', views.AppointmentCancelView.as_view(), name='cancel_appointment'),
    path('appointment/<int:appointment_id>/cancel', views.AppointmentView.as_view(show_cancel_button=True), name='appointment_cancel'),
    path('appointment/<int:appointment_id>/', views.AppointmentView.as_view(show_cancel_button=False), name='appointment_detail'),
    path('worker/<int:account_id>/<int:worker_id>/remove', views.BusinessWorkerView.as_view(show_remove_button=True), name='worker_remove'),
    path('worker/<int:account_id>/<int:worker_id>/', views.BusinessWorkerView.as_view(show_remove_button=False), name='worker_detail'),
    path('get_available_time', views.get_available_time, name='get_available_time'),
    path('registration', views.user_registration, name='user_registration'),
    path("add_business/", views.add_business, name="add_business"),
    path("view_business/<int:business_id>/", views.view_business, name="view_business"),
    path("add_business_event/<int:business_id>/", views.add_business_event, name="add_business_event"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("business_hour/<int:id>", views.BusinessHourView.as_view(), name="business_hour"),
    path("business_hour/", views.BusinessHourView.as_view(), name="business_hour_no_param"),
    path('special_day/', views.SpecialDayView.as_view(), name='special_day_create'),
    path('special_day/<int:id>/', views.SpecialDayView.as_view(), name='special_day_update_delete'),
    path('businesses/', views.AccountListView.as_view(show_dropdown = False), name='business-list'),
    path('businesses/dropdown', views.AccountListView.as_view(show_dropdown = True), name='business_list_dropdown'),
    path('logout/', LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logged_out/', views.LoggedOutView.as_view(), name='logged_out'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/', views.EventsView.as_view(), name='events_list'),
] 
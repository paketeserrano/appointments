from django.urls import path,include, re_path
from . import views
from django.contrib.auth.views import LogoutView
from appointment_calendar import settings
from django.conf.urls.static import static

conditions_skip_event = {'Event': False}
conditions_skip_event_worker = {'Event': False,
                                'Worker': False}

urlpatterns = [    
    # Paths to set up an appointment within the admin page
    path('appointment_wizard/<int:business_id>', views.BookingCreateWizardView.as_view(client_appointment=False), name='appointment_wizard'),
    path('appointment_wizard/<int:business_id>/<int:event_id>', views.BookingCreateWizardView.as_view(client_appointment=False, condition_dict = conditions_skip_event), name='appointment_for_event'),
    path('appointment_wizard/<int:business_id>/<int:event_id>/<int:worker_id>', views.BookingCreateWizardView.as_view(client_appointment=False, condition_dict = conditions_skip_event_worker), name='appointment_for_event_worker'),
    
    # Paths to set up an appointment for clients
    path('client_appointment/<int:business_id>', views.BookingCreateWizardView.as_view(client_appointment=True), name='client_appointment'),
    path('client_appointment/<int:business_id>/<int:event_id>', views.BookingCreateWizardView.as_view(client_appointment=True, condition_dict = conditions_skip_event), name='client_appointment_for_event'),
    path('client_appointment/<int:business_id>/<int:event_id>/<int:worker_id>', views.BookingCreateWizardView.as_view(client_appointment=True, condition_dict = conditions_skip_event_worker), name='client_appointment_for_event_worker'),

    path('cancel_appointment/<pk>', views.AppointmentCancelView.as_view(), name='cancel_appointment'),
    path('appointment/<int:appointment_id>/cancel', views.AppointmentView.as_view(show_cancel_button=True), name='appointment_cancel'),
    path('appointment/<int:appointment_id>/', views.AppointmentView.as_view(show_cancel_button=False), name='appointment_detail'),
    path('worker/<int:account_id>/<int:worker_id>/remove', views.BusinessWorkerView.as_view(show_remove_button=True), name='worker_remove'),
    path('worker/<int:account_id>/<int:worker_id>/', views.BusinessWorkerView.as_view(show_remove_button=False), name='worker_detail'),
    path('get_available_time', views.get_available_time, name='get_available_time'),
    path('registration', views.user_registration, name='user_registration'),
    path("add_business/", views.add_business, name="add_business"),
    path("business/<int:business_id>/", views.ViewBusiness.as_view(show_web=False), name="view_business"),
    path("add_business_event/<int:business_id>/", views.add_business_event, name="add_business_event"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("business_hour/<int:id>", views.BusinessHourView.as_view(), name="business_hour"),
    path("business_hour/", views.BusinessHourView.as_view(), name="business_hour_no_param"),
    path('special_day/', views.SpecialDayView.as_view(), name='special_day_create'),
    path('special_day/<int:id>/', views.SpecialDayView.as_view(), name='special_day_update_delete'),
    path('businesses/', views.AccountListView.as_view(show_dropdown = False), name='business-list'),
    path('businesses/dropdown', views.AccountListView.as_view(show_dropdown = True), name='business_list_dropdown'),
    path('logout/', LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logged_out/', views.LoggedOutView.as_view(), name='logged_out'),
    path('toggle-event-active/', views.toggle_event_active, name='toggle_event_active'),
    path('user_profile/<int:user_id>/', views.UserProfileView.as_view(show_web = False), name='user_profile'),    
    path('business/<int:business_id>/update_ui/', views.update_business_ui, name='update_business_ui'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/', views.EventsView.as_view(), name='events_list'),
    path('events/<int:event_id>/load_more_images/', views.load_more_images, name='load_more_images'),
    path('events/<int:event_id>/upload_photo/', views.upload_photo, name='upload_event_business_photo'),

    # Business Web pages section
    path("web/business/<int:business_id>/", views.ViewBusiness.as_view(show_web = True), name='web_business'),    
    path('web/business/service/<int:event_id>/', views.ServiceView.as_view(), name='service_view'),
    path('web/business/user/<int:business_id>/<int:user_id>/', views.UserProfileView.as_view(show_web = True), name='web_user_profile'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
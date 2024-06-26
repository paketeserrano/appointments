from django.urls import path,include, re_path
from . import views
from django.contrib.auth.views import LogoutView
from appointment_calendar import settings
from django.conf.urls.static import static

conditions_skip_event = {'Event': False}
conditions_skip_event_worker = {'Event': False,
                                'Worker': False}

urlpatterns = [   
    path('set_language/', views.set_language, name='set_language'),

    # Paths to set up an appointment within the admin page
    path('appointment_wizard/<str:business_handler>', views.BookingCreateWizardView.as_view(client_appointment=False), name='appointment_wizard'),
    path('appointment_wizard/<str:business_handler>/<str:event_handler>', views.BookingCreateWizardView.as_view(client_appointment=False, condition_dict = conditions_skip_event), name='appointment_for_event'),
    path('appointment_wizard/<str:business_handler>/<str:event_handler>/<int:worker_id>', views.BookingCreateWizardView.as_view(client_appointment=False, condition_dict = conditions_skip_event_worker), name='appointment_for_event_worker'),
    path('event_inactive/', views.event_inactive_view, name='inactive_event_page'),
    
    # Paths to set up an appointment for clients
    path('client_appointment/<str:business_handler>', views.BookingCreateWizardView.as_view(client_appointment=True), name='client_appointment'),
    path('client_appointment/<str:business_handler>/<str:event_handler>', views.BookingCreateWizardView.as_view(client_appointment=True, condition_dict = conditions_skip_event), name='client_appointment_for_event'),
    path('client_appointment/<str:business_handler>/<str:event_handler>/<int:worker_id>', views.BookingCreateWizardView.as_view(client_appointment=True, condition_dict = conditions_skip_event_worker), name='client_appointment_for_event_worker'),

    path('appointment/<int:appointment_id>/email_cancel/<uuid:cancel_uuid>', views.CancelAppointmentEmail.as_view(), name='appointment_email_cancel'),
    path('appointment/<int:appointment_id>/cancel', views.AppointmentView.as_view(show_cancel_button=True), name='appointment_cancel'),
    path('appointment/<int:appointment_id>/', views.AppointmentView.as_view(show_cancel_button=False), name='appointment_detail'),
    path('worker/<int:business_id>/<int:worker_id>/remove', views.BusinessWorkerView.as_view(show_remove_button=True), name='worker_remove'),
    path('worker/<int:business_id>/<int:worker_id>/', views.BusinessWorkerView.as_view(show_remove_button=False), name='worker_detail'),
    path('get_available_time', views.get_available_time, name='get_available_time'),      

    # Dashboard urls
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),

    # Business admin urls
    path("business/<int:business_id>/", views.ViewBusiness.as_view(show_web=False), name="view_business"),
    path("business/<int:business_id>/delete", views.delete_business, name="delete_business"),
    path('business/<int:business_id>/update_ui/', views.update_business_ui, name='update_business_ui'),
    path('business/<int:business_id>/update_address/', views.update_business_address, name='update_business_address'),
    path('business/appearance/<int:business_id>/', views.BusinessAppearanceView.as_view(), name='business_appearance'),    
    path('businesses/', views.AccountListView.as_view(show_dropdown = False), name='business-list'),
    path('businesses/dropdown', views.AccountListView.as_view(show_dropdown = True), name='business_list_dropdown'),
    path("add_business/", views.add_business, name="add_business"),
    path("add_business_event/<int:business_id>/", views.add_business_event, name="add_business_event"),    
    path("business_hour/<int:business_id>/<int:id>", views.BusinessHourView.as_view(), name="business_hour_update"),
    path("business_hour/<int:business_id>", views.BusinessHourView.as_view(), name="business_hour_create"),    
    path('special_day/<int:business_id>', views.SpecialDayView.as_view(), name='special_day_create'),
    path('special_day/<int:business_id>/<int:id>/', views.SpecialDayView.as_view(), name='special_day_update_delete'),
    path("business/invite_worker/", views.send_business_invitation, name="send_business_invitation"),
    path('business/invite_worker/confirm/<uuid:token>/', views.confirm_invitation, name='confirm_business_invitation'),

    # Blog admin urls
    path('blogs/<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),
    path("blogs/<int:business_id>/create_blog", views.create_blog, name="create_blog"),
    path("blogs/<int:blog_id>/delete_blog", views.delete_blog, name="delete_blog"),
    path('blogs/<slug:slug>/new', views.BlogPostView.as_view(), name='new_post'),
    path('blogs/<slug:slug>/<slug:post_slug>', views.BlogPostView.as_view(), name='edit_post'),

    # User admin managment urls
    path('registration', views.user_registration, name='user_registration'), 
    path('logout/', LogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL), name='logout'),
    path('login/', views.CustomLoginView.as_view(), name='user_login'),
    path('logged_out/', views.LoggedOutView.as_view(), name='logged_out'),

    # User Profile urls
    path('user_profile/<int:user_id>/', views.UserProfileView.as_view(show_web = False), name='user_profile'), 
    path('user_profile/<int:custom_user_id>/upload_photo/', views.upload_custom_user_photo, name='upload_custom_user_photo'),  
    path('user_profile/delete_custom_user_photos/', views.delete_custom_user_photos, name='delete_custom_user_photos'),
    path('user_profile/<int:custom_user_id>/load_more_images/', views.load_more_custom_user_images, name='load_more_custom_user_images'),
    path('user/appointments/', views.appointments, name='user_appointments'),

    # Invitees urls
    path('search_clients/', views.search_invitees, name='search_invitees'),
    path('clients/<int:invitee_id>/', views.invitee_detail_view, name='invitee_detail'),
    
    # Event admin urls
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/', views.EventsView.as_view(), name='events_list'),
    path('events/<int:event_id>/load_more_images/', views.load_more_images, name='load_more_images'),
    path('events/<int:event_id>/upload_photo/', views.upload_event_photo, name='upload_event_business_photo'),
    path('event/<int:event_id>/add_question/', views.add_event_question, name='add_event_question'),
    path('event/<int:event_id>/question/<int:question_id>/', views.event_question, name='event_question'),
    path('event/<int:event_id>/edit_question/<int:question_id>/', views.edit_question, name='edit_event_question'),
    path('event/<int:event_id>/remove_question/<int:question_id>/', views.remove_event_question, name='remove_event_question'),
    path('events/delete_photos/', views.delete_event_photos, name='delete_event_business_photos'),
    path('update-event-status/', views.update_event_status, name='update-event-status'),
    path('toggle-event-active/', views.toggle_event_active, name='toggle_event_active'),
    path('events/<int:event_id>/remove_worker/<int:user_id>', views.event_remove_worker, name='event_remove_worker'),
    path('event/<int:event_id>/add_location/', views.add_event_location, name='add_event_location'),
    path('event/<int:event_id>/location/<int:location_id>/', views.get_event_location, name='get_event_location'),
    path('event/<int:event_id>/edit_location/<int:location_id>/', views.edit_event_location, name='edit_event_location'),
    path('event/<int:event_id>/remove_location/<int:location_id>/', views.remove_event_location, name='remove_event_location'),

    # Business Web pages section urls
    path("web/<str:business_handler>/", views.ViewBusiness.as_view(show_web = True), name='web_business'),    
    path('web/<str:business_handler>/service/<str:event_handler>/', views.ServiceView.as_view(), name='service_view'),
    path('web/<str:business_handler>/user/<int:user_id>/', views.UserProfileView.as_view(show_web = True), name='web_user_profile'),
    path('web/<str:business_handler>/blog/<slug:slug>/', views.BlogView.as_view(), name='view_blog'),

    path('ckeditor5/upload1/', views.custom_upload_file, name="custom_upload_file"),

    # Website home pages
    path('', views.home, name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
from django.urls import path,include, re_path
from . import views

urlpatterns = [    
    path('appointment_wizard/<int:business_id>', views.BookingCreateWizardView.as_view(), name='appointment_wizard'),
    path('cancel_appointment/<pk>', views.AppointmentCancelView.as_view(), name='cancel_appointment'),
    path('appointment/<int:appointment_id>/cancel', views.AppointmentView.as_view(show_cancel_button=True), name='appointment_cancel'),
    path('appointment/<int:appointment_id>/', views.AppointmentView.as_view(show_cancel_button=False), name='appointment_detail'),
    path('worker/<int:account_id>/<int:worker_id>/remove', views.BusinessWorkerView.as_view(show_remove_button=True), name='worker_remove'),
    path('worker/<int:account_id>/<int:worker_id>/', views.BusinessWorkerView.as_view(show_remove_button=False), name='worker_detail'),
    path('get_available_time', views.get_available_time, name='get_available_time'),
    #path('appointment/<int:business_id>/<int:event_id>', views.appointment, name='appointment'),
    path('registration', views.user_registration, name='user_registration'),
    path("add_business/", views.add_business, name="add_business"),
    path("view_business/<int:business_id>/", views.view_business, name="view_business"),
    path("add_business_event/<int:business_id>/", views.add_business_event, name="add_business_event"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("business_hour/<int:id>", views.BusinessHourView.as_view(), name="business_hour"),
    path("business_hour/", views.BusinessHourView.as_view(), name="business_hour_no_param"),
] 
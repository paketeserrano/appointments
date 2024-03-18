from django.urls import path,include, re_path
from . import views

urlpatterns = [    
    path('appointment_wizard/<int:business_id>', views.BookingCreateWizardView.as_view(), name='appointment_wizard'),
    path('get_available_time', views.get_available_time, name='get_available_time'),
    path('appointment/<int:business_id>/<int:event_id>', views.appointment, name='appointment'),
    path('registration', views.user_registration, name='user_registration'),
    path("add_business/", views.add_business, name="add_business"),
    path("view_business/<int:business_id>/", views.view_business, name="view_business"),
    path("add_business_event/<int:business_id>/", views.add_business_event, name="add_business_event"),
    path('test/<int:pepe>', views.HomePageView.as_view(), name = 'home_page'),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
] 
from django.urls import path
from chatbot import views

urlpatterns = [
    path('', views.chatbot_home, name='chatbot_home'),
    path('get_response/', views.get_response, name='get_response'),
    path('clear_history/', views.clear_history, name='clear_history'),
    path('upload_file/', views.upload_file, name='upload_file'),  # New endpoint for file upload
]
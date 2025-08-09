from django.urls import path, include

urlpatterns = [
    # ... existing URL patterns
    path('voice/', include('agrisarthi.voice.urls')),
]
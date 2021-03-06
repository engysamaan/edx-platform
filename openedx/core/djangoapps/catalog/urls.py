"""
Defines the URL routes for this app.
"""
from __future__ import absolute_import

from django.conf.urls import url

from . import views

app_name = 'catalog'
urlpatterns = [
    url(r'^management/cache_programs/$', views.cache_programs, name='cache_programs'),
]

from django.conf.urls.defaults import *

from views import *

urlpatterns = patterns(
    '',
    (r'^$', index),
    (r'^about/$', about),
    (r'^program/(?P<id>\d+)/feed/$', program_feed),
    (r'^program/(?P<id>\d+)/$', program),
    (r'^update_status/(?P<id>\d+)/$', update_status),
    (r'^programadmin/$', list_program),
    (r'^programadmin/new/$', new_program),
    (r'^programadmin/(?P<id>\d+)/edit/$', edit_program),
    (r'^programadmin/save/$', save_program),
    (r'^createuser/$', createuser),
    (r'^scheduled/$', scheduled),
    (r'^save_episode/$', save_episode),
)

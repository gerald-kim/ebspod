# -*- coding: utf-8 -*-

from google.appengine.ext.db import djangoforms
from django import newforms as forms

class ProgramForm(forms.Form):
    id = forms.IntegerField(required=False, widget=forms.HiddenInput() )
    title = forms.CharField(label=u"프로그램명", max_length=50, widget=forms.TextInput(attrs={'size': 20}))
    description = forms.CharField(label=u"설명", required=False, max_length=50, widget=forms.Textarea)
#    description = forms.TextField(label=u"설명", max_length=400 )
    mon = forms.BooleanField(required=False, initial=False)
    tue = forms.BooleanField(required=False, initial=False)
    wed = forms.BooleanField(required=False, initial=False)
    thu = forms.BooleanField(required=False, initial=False)
    fri = forms.BooleanField(required=False, initial=False)
    sat = forms.BooleanField(required=False, initial=False)
    sun = forms.BooleanField(required=False, initial=False)
    
    start = forms.TimeField() 
    end = forms.TimeField() 
    
class EpisodeForm(forms.Form):
    program_id = forms.IntegerField()
    url = forms.CharField()
    
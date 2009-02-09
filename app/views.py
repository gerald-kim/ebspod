# -*- coding: utf-8 -*-

# Python imports
import datetime
import urllib
import logging 
import pytz

# AppEngine imports
from google.appengine.api import users
from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.ext.db import djangoforms
from google.appengine.runtime import DeadlineExceededError

# Django imports
# TODO(guido): Don't import classes/functions directly.
from django import newforms as forms
from django.http import Http404
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render_to_response

import django.template

# Local imports
from models import *
from forms import *
from view_helpers import *

app_tz = pytz.timezone( settings.TIME_ZONE )    


### Request handlers ###
@login_required
def about(request):
    return respond( request, 'about.html' )
    
    
@login_required
def index( request ):
#    if user:
#        ebsPodUser = EbsPodUser.get_by_key_name( user.email() )
#        #print ebsPodUser.id()
#    if not ebsPodUser :
#        greeting = ("등록된 사용자만 사용할 수 있습니다. 다시 <a href=\"%s\">로그인 하세요</a>." %
#                  users.create_login_url("/"))
#        response.write("<html><body>%s</body></html>" % greeting)
#        return response
    programs = Program.all()
    
    return respond(request, 'index.html', { 'programs': programs } )

def program( request, id ):
    program = Program.get_by_id( long(id) )
    if None == program:
        raise Http404

    episodes = Episode.gql( "WHERE program = :1 and created > :2 order by created desc", program, (datetime.datetime.now()-datetime.timedelta( days = 30 )) )
    server_url = request.META['SERVER_NAME']+':'+request.META['SERVER_PORT']
    return respond(request, 'program.html', {'program': program, 'episodes':episodes, 'server_url':server_url} )

def program_feed( request, id ):
    response = HttpResponse()
    response
    program = Program.get_by_id( long(id) )
    if None == program:
        raise Http404
    episodes = Episode.gql( "WHERE program = :1 and created > :2 order by created desc", program, (datetime.datetime.now()-datetime.timedelta( days = 30 )) )
    
    c = django.template.Context( {'program':program, 'episodes': episodes } )
    t = django.template.loader.get_template('program_feed.html')
    return HttpResponse(t.render( c ), mimetype="text/xml")
    
def scheduled(request):
    """scheduled programs"""
    
    now = datetime.datetime.now( app_tz )
    td = datetime.timedelta( seconds = 90 )
    
    q = Program.gql( "where "  + Program.day_select_query() + 
        " and status = 'pending' and start >= :1 and start < :2",  (now-td).time(), (now+td).time() )
    program = q.get()
    c = django.template.Context( {'program':program} )
    t = django.template.loader.get_template('scheduled.json')
    return HttpResponse(t.render( c ), mimetype="text/plain")

def update_status( request, id ):
    response = HttpResponse()
    program = Program.get_by_id( long(id) )
    if None == program:
        response.write( '0' )
        return response

    program.status = request['status']
    program.save()
    response.write( '1' )
    return response
    

def createuser( request ):
    response = HttpResponse()
    if users.is_current_user_admin():
        u = EbsPodUser( key_name = request['email'], v = "v" )
        u.save()
    response.write( loader.render_to_string('index.html' ) )
    return response


def list_program( request ):
    programs = Program.all()

    return respond( request, 'program_list.html', 
                    { 'programs': programs } )


def new_program( request ):
    logging.info( "FORMS" + str(dir(forms) ) )
    form = ProgramForm()
    return respond( request, 'program_form.html', {'form': form} )

def edit_program( request, id ):
    program = Program.get_by_id( long(id) )
    if None == program:
        raise Http404
    
    form = ProgramForm( {'id': program.key().id(),
                         'title': program.title,
                         'description': program.description,
                         'mon': program.mon,
                         'tue': program.tue,
                         'wed': program.wed,
                         'thu': program.thu,
                         'fri': program.fri,
                         'sat': program.sat,
                         'sun': program.sun,
                         'start': str( program.start )[:5],
                         'end': str( program.end )[:5],
                          } )
    
    return respond( request, 'program_form.html', {'form': form, 'program':program} )

def save_program( request ):
    request.encoding = 'utf-8'
    
    form = ProgramForm( request.POST )
    if form.is_valid():
        data = form.clean_data
        if data['id']:
            program = Program.get_by_id( long(data['id']) )
        else:
            program = Program()
        program.title = data['title']
        program.description = data['description']
        program.mon = data['mon']
        program.tue = data['tue']
        program.wed = data['wed']
        program.thu = data['thu']
        program.fri = data['fri']
        program.sat = data['sat']
        program.sun = data['sun']
        program.start = data['start']
        program.end = data['end']
        program.save()
        return HttpResponseRedirect( '/programadmin/' + str(program.key().id()) + '/edit/' )
#        return respond( request, 'program_form.html', {'form': form} )
    else:
        return respond( request, 'program_form.html', {'form': form} )


def save_episode( request ):
    request.encoding = 'utf-8'
    response = HttpResponse()
    
    form = EpisodeForm( request.GET )
    if form.is_valid():
        data = form.clean_data
        p = Program.get_by_id( long(data['program_id']) )
        e = Episode( program = p, url = data['url'] )
        e.save()
        logging.info(  e.key().id() )
        response.write( '1' )
    else:    
        response.write( '0' )
    return response
    

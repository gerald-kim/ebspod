# -*- coding: utf-8 -*-

from appengine_django.models import BaseModel
from google.appengine.ext import db

import settings
import datetime
import pytz

class Program( BaseModel ):
    STATUS_CHOICE = set(["pending", "ready", "recording"])
    
    title = db.StringProperty()
    description = db.StringProperty()

    mon = db.BooleanProperty(default=False)
    tue = db.BooleanProperty(default=False)
    wed = db.BooleanProperty(default=False)
    thu = db.BooleanProperty(default=False)
    fri = db.BooleanProperty(default=False)
    sat = db.BooleanProperty(default=False)
    sun = db.BooleanProperty(default=False)
  
    start = db.TimeProperty()
    end = db.TimeProperty()
    
    status = db.StringProperty(default='pending', choices=STATUS_CHOICE)
    
    created = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    
    """

    days_of_weeks = models.PositiveSmallIntegerField( '방송요일' )
    created = models.DateTimeField( default=datetime.datetime.now )
    modified = models.DateTimeField( default=datetime.datetime.now )
    """
    
    def days_of_week( self ):
        l = []
        if self.mon:
            l.append( unicode("월", 'utf-8') )
        if self.tue:
            l.append( unicode("화", 'utf-8') )
        if self.wed:
            l.append( unicode("수", 'utf-8') )
        if self.thu:
            l.append( unicode("목", 'utf-8') )
        if self.fri:
            l.append( unicode("금", 'utf-8') )
        if self.sat:
            l.append( unicode("토", 'utf-8') )
        if self.sun:
            l.append( unicode("일", 'utf-8') )
        from string import join
        return join( l, ', ' )

    @classmethod
    def day_select_query(cls):
        """generate day select query"""
        DAYS_OF_WEEK_FIELDS = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
        
        now = datetime.datetime.now( pytz.timezone( settings.TIME_ZONE ) )
        days_of_week = datetime.datetime.weekday( now )
        field = DAYS_OF_WEEK_FIELDS[days_of_week]
        
        return "%s = true" % ( field )
        

class Episode( BaseModel ):
    program = db.ReferenceProperty( Program )
    url = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

    def created_kst( self ):
        return self.created.replace(tzinfo=pytz.utc).astimezone( pytz.timezone( settings.TIME_ZONE ) )
        

class Account( BaseModel ):
  user = db.UserProperty(required=True)
  email = db.EmailProperty(required=True)  # key == <email>
  created = db.DateTimeProperty(auto_now_add=True)

  # Current user's Account.  Updated by middleware.AddUserToRequestMiddleware.
  current_user_account = None

  @classmethod
  def get_account_for_user(cls, user):
    """Get the Account for a user, creating a default one if needed."""
    email = user.email()
    assert email
    key = '<%s>' % email
    # Since usually the account already exists, first try getting it
    # without the transaction implied by get_or_insert().
    account = cls.get_by_key_name(key)
    if account is not None:
      return account

    return cls.get_or_insert(key, user=user, email=email, fresh=True)
# -*- coding: utf-8 -*-

# AppEngine imports
from google.appengine.api import users
from google.appengine.runtime import DeadlineExceededError

# Django imports
from django.http import HttpResponse, HttpResponseRedirect
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.shortcuts import render_to_response
import django.template

import os

### Helper functions ###
def respond(request, template, context=None):
    """Helper to render a response, passing standard stuff to the response.

    Args:
        request: The request object.
        template: The template name; '.html' is appended automatically.
        context: A dict giving the template parameters; modified in-place.

    Returns:
        Whatever render_to_response(template, context) returns.

    Raises:
        Whatever render_to_response(template, context) raises.
    """

    if context is None:
        context = {}
#    if request.user is not None:
#        account = models.Account.current_user_account
#        must_choose_nickname = not account.user_has_selected_nickname()

    context['request'] = request
    context['user'] = request.user
    context['is_admin'] = request.user_is_admin

    full_path = request.get_full_path().encode('utf-8')
    if request.user is None:
        context['sign_in'] = users.create_login_url(full_path)
    else:
        context['sign_out'] = users.create_logout_url(full_path)
    try:
        return render_to_response(template, context)
    except DeadlineExceededError:
        logging.exception('DeadlineExceededError')
        return HttpResponse('DeadlineExceededError')
    except MemoryError:
        logging.exception('MemoryError')
        return HttpResponse('MemoryError')
    except AssertionError:
        logging.exception('AssertionError')
        return HttpResponse('AssertionError')

### Decorators for request handlers ###
def login_required(func):
  """Decorator that redirects to the login page if you're not logged in."""

  def login_wrapper(request, *args, **kwds):
    if request.user is None:
      return HttpResponseRedirect(
          users.create_login_url(request.get_full_path().encode('utf-8')))
    return func(request, *args, **kwds)

  return login_wrapper

def admin_required(func):
  """Decorator that insists that you're logged in as administratior."""

  def admin_wrapper(request, *args, **kwds):
    if request.user is None:
      return HttpResponseRedirect(
          users.create_login_url(request.get_full_path().encode('utf-8')))
    if not request.user_is_admin:
      return HttpResponseForbidden('You must be admin in for this function')
    return func(request, *args, **kwds)

  return admin_wrapper


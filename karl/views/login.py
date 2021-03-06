# Copyright (C) 2008-2009 Open Society Institute
#               Thomas Moroz: tmoroz@sorosny.org
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License Version 2 as published
# by the Free Software Foundation.  You may not use, modify or distribute
# this program under any other version of the GNU General Public License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import logging

from datetime import datetime
from urlparse import urljoin

from repoze.who.plugins.zodb.users import get_sha_password

from pyramid.httpexceptions import HTTPFound
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.renderers import render_to_response
from pyramid.security import forget
from pyramid.security import remember
from pyramid.settings import asbool
from pyramid.settings import aslist
from pyramid.url import resource_url

from karl.application import is_normal_mode
from karl.utils import find_profiles
from karl.utils import find_site
from karl.utils import find_users

from karl.views.api import TemplateAPI

log = logging.getLogger(__name__)


def _fixup_came_from(request, came_from):
    came_from = urljoin(request.application_url, came_from)
    if came_from.endswith('login.html'):
        came_from = came_from[:-len('login.html')]
    elif came_from.endswith('logout.html'):
        came_from = came_from[:-len('logout.html')]
    return came_from


def _authenticate(context, login, password):
    userid = None
    users = find_users(context)
    for authenticate in (password_authenticator, impersonate_authenticator):
        userid = authenticate(users, login, password)
        if userid:
            break
    return userid


def login_view(context, request):
    settings = request.registry.settings
    came_from = request.session.get('came_from', request.url)
    came_from = _fixup_came_from(request, came_from)
    request.session['came_from'] = came_from

    submitted = request.params.get('form.submitted', None)
    if submitted:
        # identify
        login = request.POST.get('login')
        password = request.POST.get('password')
        if login is None or password is None:
            return HTTPFound(location='%s/login.html'
                                        % request.application_url)
        max_age = request.registry.settings.get('login_cookie_max_age', '36000')
        max_age = int(max_age)

        # authenticate
        reason = 'Bad username or password'
        userid = _authenticate(context, login, password)

        # if not successful, try again
        if not userid:
            redirect = request.resource_url(
                request.root, 'login.html', query={'reason': reason})
            return HTTPFound(location=redirect)

        # else, remember
        admin_only = asbool(request.registry.settings.get('admin_only', ''))
        admins = aslist(request.registry.settings.get('admin_userids', ''))
        if not admin_only or userid in admins:
            return remember_login(context, request, userid, max_age)
        else:
            return site_down_view(context, request)

    page_title = 'Login to %s' % settings.get('system_name', 'KARL') # Per #366377, don't say what screen
    api = TemplateAPI(context, request, page_title)
    api.status_message = request.params.get('reason', None)
    response = render_to_response(
        'templates/login.pt',
        dict(
            api=api,
            app_url=request.application_url),
        request=request)
    forget_headers = forget(request)
    response.headers.extend(forget_headers)
    return response


def site_down_view(context, request):
    page_title = "Karl is down for maintainance"
    api = TemplateAPI(context, request, page_title)
    response = render_to_response(
        'templates/down.pt',
        dict(
            api=api,
            app_url=request.application_url),
        request=request)
    forget_headers = forget(request)
    response.headers.extend(forget_headers)
    return response


def api_login_view(context, request):
    login = request.json_body.get('login')
    password = request.json_body.get('password')
    userid = _authenticate(context, login, password)
    if not userid:
        return {'error': 'login failed'}
    remember_headers = remember(request, userid)
    request.response.headers.extend(remember_headers)
    policy = request.registry.queryUtility(IAuthenticationPolicy)
    jwtauth = policy._policies[0]
    token = jwtauth.encode_jwt(request, claims={'sub': userid})
    result = {'token': 'JWT token="' + token.decode('utf-8') + '"'}
    return result


def remember_login(context, request, userid, max_age):
    remember_headers = remember(request, userid, max_age=max_age)

    # log the time on the user's profile, unless in read only mode
    read_only = not is_normal_mode(request.registry)
    if not read_only:
        profiles = find_profiles(context)
        if profiles is not None:
            profile = profiles.get(userid)
            if profile is not None:
                profile.last_login_time = datetime.utcnow()

    # redirect
    came_from = request.session.pop('came_from')
    return HTTPFound(headers=remember_headers, location=came_from)


def logout_view(context, request, reason='Logged out'):
    site = find_site(context)
    site_url = resource_url(site, request)
    request.session['came_from'] = site_url
    query = {'reason': reason}
    login_url = resource_url(site, request, 'login.html', query=query)

    redirect = HTTPFound(location=login_url)
    redirect.headers.extend(forget(request))
    return redirect


def password_authenticator(users, login, password):
    user = users.get(login=login)
    if user and user['password'] == get_sha_password(password):
        return user['id']


def impersonate_authenticator(users, login, password):
    if not ':' in password:
        return

    admin_login, password = password.split(':', 1)
    admin = users.get(login=admin_login)
    user = users.get(login=login)
    if user and admin and 'group.KarlAdmin' in admin['groups']:
        if password_authenticator(users, admin_login, password):
            log.info("Superuser %s is impersonating %s", admin['id'],
                     user['id'])
            return user['id']

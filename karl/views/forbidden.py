from pyramid.renderers import render_to_response
from pyramid.url import resource_url

from karl.views.api import TemplateAPI
from karl.utils import find_site

def forbidden(context, request):
    site = find_site(context)
    request.session['came_from'] = request.url
    api = TemplateAPI(context, request, 'Forbidden')
    request.response.status = '200 OK'

    blacklisted = request.session.get('access_blacklisted', False)
    if blacklisted:
        notice = getattr(site, 'restricted_notice', '')
        return render_to_response(
            'templates/forbidden_blacklisted.pt',
            dict(api=api, notice=notice),
            request=request)

    if api.userid:
        login_url = resource_url(site, request, 'login.html')
    else:
        login_url = resource_url(
            site, request, 'login.html', query={'reason': 'Not logged in'})
    return {
        'api': api,
        'login_form_url': login_url,
        'homepage_url': resource_url(site, request)
    }

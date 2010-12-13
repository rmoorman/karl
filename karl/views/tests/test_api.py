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

import unittest
from repoze.bfg import testing
from karl import testing as karltesting

class TemplateAPITests(unittest.TestCase):
    def setUp(self):
        testing.cleanUp()

    def tearDown(self):
        testing.cleanUp()

    def _getTargetClass(self):
        from karl.views.api import TemplateAPI
        return TemplateAPI

    def _makeOne(self, context, request, page_title=''):
        return self._getTargetClass()(context, request, page_title)

    def test_community_info(self):
        from zope.interface import Interface
        from zope.interface import directlyProvides
        from karl.models.interfaces import ICommunityInfo
        from karl.models.interfaces import ICommunity
        testing.registerAdapter(DummyAdapter,
                                (Interface, Interface), ICommunityInfo)
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        community_info = api.community_info
        self.assertEqual(community_info.context, context)

    def test_recent_items(self):
        from zope.interface import Interface
        from zope.interface import directlyProvides
        from karl.models.interfaces import ICommunity
        from karl.models.interfaces import ICatalogSearch
        from karl.models.interfaces import IGridEntryInfo
        testing.registerAdapter(DummySearchAdapter, Interface, ICatalogSearch)
        testing.registerAdapter(DummyAdapter,
                                (Interface, Interface), IGridEntryInfo)
        f = testing.DummyModel()
        testing.registerModels({'/communities/1/file':f})
        context = testing.DummyModel()
        directlyProvides(context, ICommunity)
        context.searchresults = [f]
        context.catalog = karltesting.DummyCatalog({1:'/communities/1/file'})
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        recent_items = api.recent_items
        self.assertEqual(len(recent_items), 1)
        self.assertEqual(recent_items[0].context, f)

    def test_tag_users(self):
        from karl.models.interfaces import ITagQuery
        from zope.interface import Interface
        testing.registerAdapter(DummyTagQuery, (Interface, Interface),
                                ITagQuery)
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.tag_users, ['a'])

    def test_people_url(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.people_url, 'http://example.com/profiles')

    def test_status_message(self):
        context = testing.DummyModel()
        request = testing.DummyRequest({'status_message':'abc'})
        api = self._makeOne(context, request)
        self.assertEqual(api.status_message, 'abc')

    def test_generic_layout(self):
        renderer = testing.registerDummyRenderer(
            'karl.views:templates/generic_layout.pt')
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        api.generic_layout(a=1)
        renderer.assert_(a=1)

    def test_anonymous_layout(self):
        renderer = testing.registerDummyRenderer(
            'karl.views:templates/anonymous_layout.pt')
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        api.anonymous_layout(a=1)
        renderer.assert_(a=1)

    def test_community_layout(self):
        renderer = testing.registerDummyRenderer(
            'karl.views:templates/community_layout.pt')
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        api.community_layout(a=1)
        renderer.assert_(a=1)

    def test_getitem(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertRaises(ValueError, api.__getitem__, 'a')

    def test_render_sidebar_no_adapter(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.render_sidebar(), '')

    def test_render_sidebar_w_direct_adapter(self):
        from zope.interface import Interface
        from karl.views.interfaces import ISidebar
        context = testing.DummyModel()
        _called_with = []
        def _factory(context, request):
            def _render(api):
                _called_with.append(api)
                return 'SIDEBAR'
            return _render
        testing.registerAdapter(_factory, (Interface, Interface), ISidebar)
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.render_sidebar(), 'SIDEBAR')

    def test_render_sidebar_w_acquired_adapter(self):
        from zope.interface import directlyProvides
        from zope.interface import Interface
        from karl.models.interfaces import ICommunity
        from karl.views.interfaces import ISidebar
        parent = testing.DummyModel()
        directlyProvides(parent, ICommunity)
        context = parent['child'] = testing.DummyModel()
        _called_with = []
        def _factory(context, request):
            def _render(api):
                _called_with.append(api)
                return 'SIDEBAR'
            return _render
        testing.registerAdapter(_factory, (ICommunity, Interface), ISidebar)
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.render_sidebar(), 'SIDEBAR')

    def test_render_footer_no_adapter(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        renderer = testing.registerDummyRenderer(
            'templates/footer.pt')
        api.render_footer()
        renderer.assert_(api=api)

    def test_render_footer_w_direct_adapter(self):
        from zope.interface import Interface
        from karl.views.interfaces import IFooter
        context = testing.DummyModel()
        _called_with = []
        def _factory(context, request):
            def _render(api):
                _called_with.append(api)
                return 'FOOTER'
            return _render
        testing.registerAdapter(_factory, (Interface, Interface), IFooter)
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.render_footer(), 'FOOTER')

    def test_render_footer_w_acquired_adapter(self):
        from zope.interface import directlyProvides
        from zope.interface import Interface
        from karl.models.interfaces import ICommunity
        from karl.views.interfaces import IFooter
        parent = testing.DummyModel()
        directlyProvides(parent, ICommunity)
        context = parent['child'] = testing.DummyModel()
        _called_with = []
        def _factory(context, request):
            def _render(api):
                _called_with.append(api)
                return 'FOOTER'
            return _render
        testing.registerAdapter(_factory, (ICommunity, Interface), IFooter)
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.render_footer(), 'FOOTER')

    def test_default_logo_url(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.logo_url, api.static_url + '/images/logo.gif')

    def test_custom_logo_url(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        from repoze.bfg.interfaces import ISettings
        settings = karltesting.DummySettings()
        settings.logo_path = 'mylogo.png'
        testing.registerUtility(settings, ISettings)
        api = self._makeOne(context, request)
        self.assertEqual(api.logo_url, api.static_url + '/mylogo.png')

    def test_kaltura_info_empty(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        api = self._makeOne(context, request)
        self.assertEqual(api.kaltura_info, {'enabled': False})

    def test_kaltura_info(self):
        context = testing.DummyModel()
        request = testing.DummyRequest()
        from repoze.bfg.interfaces import ISettings
        settings = karltesting.DummySettings()
        settings.kaltura_enabled = 'true'
        # kaltura_client_session missing
        settings.kaltura_partner_id = '123456'
        settings.kaltura_sub_partner_id = '12345600'
        settings.kaltura_admin_secret = '123456789abcdef123456789abcdef12'
        settings.kaltura_user_secret = '0123456789abcdef123456789abcdef1'
        settings.kaltura_kcw_uiconf_id = '9999999'
        settings.kaltura_player_uiconf_id = '8888888'
        settings.kaltura_player_cache_st = '77777777'
        testing.registerUtility(settings, ISettings)
        api = self._makeOne(context, request)
        self.assertEqual(api.kaltura_info, dict(
            enabled = True,
            partner_id = '123456',
            sub_partner_id = '12345600',
            session_url = 'http://example.com/kaltura_create_session.json',
            admin_secret = '123456789abcdef123456789abcdef12',
            user_secret = '0123456789abcdef123456789abcdef1',
            kcw_uiconf_id = '9999999',
            player_uiconf_id = '8888888',
            player_cache_st = '77777777',
            local_user = None,
            ))
        # secrets are not sent to client
        self.assertEqual(api.render_karl_client_data(), '<script type="text/javascript">\nwindow.karl_client_data = {"kaltura": {"sub_partner_id": "12345600", "player_uiconf_id": "8888888", "enabled": true, "local_user": null, "player_cache_st": "77777777", "kcw_uiconf_id": "9999999", "partner_id": "123456", "session_url": "http://example.com/kaltura_create_session.json"}};\n</script>')
        
        settings.kaltura_client_session = 'false'
        api = self._makeOne(context, request)
        self.assertEqual(api.kaltura_info, dict(
            enabled = True,
            partner_id = '123456',
            sub_partner_id = '12345600',
            session_url = 'http://example.com/kaltura_create_session.json',
            admin_secret = '123456789abcdef123456789abcdef12',
            user_secret = '0123456789abcdef123456789abcdef1',
            kcw_uiconf_id = '9999999',
            player_uiconf_id = '8888888',
            player_cache_st = '77777777',
            local_user = None,
            ))
        # secrets are not sent to client
        self.assertEqual(api.render_karl_client_data(), '<script type="text/javascript">\nwindow.karl_client_data = {"kaltura": {"sub_partner_id": "12345600", "player_uiconf_id": "8888888", "enabled": true, "local_user": null, "player_cache_st": "77777777", "kcw_uiconf_id": "9999999", "partner_id": "123456", "session_url": "http://example.com/kaltura_create_session.json"}};\n</script>')
        
        settings.kaltura_client_session = 'true'
        api = self._makeOne(context, request)
        self.assertEqual(api.kaltura_info, dict(
            enabled = True,
            partner_id = '123456',
            sub_partner_id = '12345600',
            admin_secret = '123456789abcdef123456789abcdef12',
            user_secret = '0123456789abcdef123456789abcdef1',
            kcw_uiconf_id = '9999999',
            player_uiconf_id = '8888888',
            player_cache_st = '77777777',
            local_user = None,
            # no session_url means client side session management
            ))
        # secrets are sent to client
        self.assertEqual(api.render_karl_client_data(), '<script type="text/javascript">\nwindow.karl_client_data = {"kaltura": {"admin_secret": "123456789abcdef123456789abcdef12", "user_secret": "0123456789abcdef123456789abcdef1", "sub_partner_id": "12345600", "player_uiconf_id": "8888888", "enabled": true, "local_user": null, "player_cache_st": "77777777", "kcw_uiconf_id": "9999999", "partner_id": "123456"}};\n</script>')


class DummyTagQuery:
    def __init__(self, context, request):
        self.tagusers = ['a']


class DummyAdapter:
    def __init__(self, context, request):
        self.context = context
        self.request = request

class DummySearchAdapter:
    def __init__(self, context):
        self.context = context

    def __call__(self, *arg, **kw):
        results = self.context.searchresults
        def resolver(x):
            for thing in self.context.searchresults:
                if thing == x:
                    return thing
        return len(results), results, resolver


"""
Views related to JSON API for archive to box feature.
"""
import datetime
import functools
import logging
import uuid

from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPAccepted, HTTPBadRequest
from pyramid.security import Allow
from pyramid.traversal import resource_path
from pyramid.url import urlencode
from pyramid.view import view_config
from repoze.workflow import get_workflow

from karl.models.interfaces import (
    ICatalogSearch,
    ICommunities,
    ICommunity,
    ISite,
)
from karl.content.interfaces import (
    ICommunityFile,
    ICalendarCategory,
    IBlog,
    ICalendar,
    ICommunityRootFolder,
    IWiki,
    IWikiPage,
    IBlogEntry,
)
from karl.security.policy import VIEW
from karl.views.acl import modify_acl
from karl.utils import coarse_datetime_repr

from .client import BoxClient, find_box
from .queue import RedisArchiveQueue

logger = logging.getLogger(__name__)

# Work around for lack of 'view_defaults' in earlier version of Pyramid
box_api_view = functools.partial(
    view_config,
    route_name='archive_to_box',
    permission='administer',
    renderer='json')


def action(action):
    """
    Custom predicate that examines the value of an 'action' sent in a JSON
    payload.
    """
    def predicate(context, request):
        try:
            return request.json_body.get('action') == action
        except ValueError:
            return False
    return predicate


class ArchiveToBoxAPI(object):
    """
    Views related to JSON API for archive to box feature.
    """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    @reify
    def queue(self):
        return RedisArchiveQueue.from_settings(self.request.registry.settings)

    @box_api_view(
        context=ISite,
        request_method='GET',
        name='token')
    def token(self):
        """
        GET: /arc2box/token

        Checks to see if access token for Box API is up to date and usable.
        Returns JSON:

            {"valid": true}

            or

            {"valid": false, "url": <box_login_url>}
        """
        box = find_box(self.context)
        client = BoxClient(box, self.request.registry.settings)
        if client.check_token():
            return {'valid': True}

        if not box.state:
            box.state = str(uuid.uuid4())
        query = {
            'response_type': 'code',
            'client_id': client.client_id,
            'state': box.state,
            'redirect_uri': self.request.resource_url(box, '@@box_auth'),
        }
        url = client.authorize_url + '?' + urlencode(query)

        logger.info('arc2box: Got token')
        return {'valid': False, 'url': url}

    @box_api_view(
        context=ICommunities,
        request_method='GET')
    def get_communities_to_archive(self):
        """
        GET: /arc2box/communities/

        Returns a list of communities eligible to be archived.  Accepts the
        following query parameters, none of which are required:

            + last_activity: Integer number of days. Will only include
              communities with no updates younger than given number of days.
              Default is 540 days (roughly 18 months).
            + filter: Text used as a filter on the communitie's title.  Only
              matching communities will be returned.  By default, no filtering
              is done.
            + limit: Integer number of results to return.  Default is to return
              all results.
            + offset: Integer index of first result to return. For use in
              conjunction with `limit` in order to batch results.

        Results are ordered by time of last activity, oldest first.

        Returns a list of objects, with each object containing the following
        keys:

            + id: docid of the community.
            + name: The name of the community (URL name).
            + title: The title (display name) of the community.
            + last_activity: Time of last activity on this community.
            + url: URL of the community.
            + items: integer count of number documents in this community.
            + status: workflow state with regards to archive process,

        The possible values of `status` are:

            + null: The community is in normal mode, not currently in any
                    archive state.
            + "copying": The archiver is in the process of copying community
                         content to Box.
            + "reviewing": The archiver has finished copying community content
                           to Box and is ready for an administrator to review
                           the content in Box before proceeding.
            + "removing": The archiver is in the process of removing content
                          from the community.  A transition to this state is
                          the point of no return.
            + "archived": The archiver has copied all community content to the
                          Box archive and removed the content from Karl. The
                          community is mothballed.
            + "exception": An exception has occurred while processing this
                           community.
        """
        params = self.request.params
        last_activity = int(params.get('last_activity', 540))
        filter_text = params.get('filter')
        limit = int(params.get('limit', 0))
        offset = int(params.get('offset', 0))

        search = ICatalogSearch(self.context)
        now = datetime.datetime.now()
        timeago = now - datetime.timedelta(days=last_activity)
        count, docids, resolver = search(
            interfaces=[ICommunity],
            content_modified=(None, coarse_datetime_repr(timeago)),
            sort_index='content_modified',
            reverse=True)

        def results(docids=docids, limit=limit, offset=offset):
            if offset and not filter_text:
                docids = docids[offset:]
                offset = 0
            for docid in docids:
                if offset:
                    offset -= 1
                    continue
                community = resolver(docid)
                if (not filter_text or
                    filter_text.lower() in community.title.lower()):
                    yield community
                    if limit:
                        limit -= 1
                        if not limit:
                            break

        route_url = self.request.route_url

        def record(community):
            path = resource_path(community)
            count = 0
            for interface in [IBlogEntry,
                               ICommunityFile,
                               ICalendarCategory,
                               IBlog,
                               ICalendar,
                               ICommunityRootFolder,
                               IWiki,
                               IWikiPage]:
                items, _, _ = search(path=path, interfaces=[interface])
                count += items
            return {
                'id': community.docid,
                'name': community.__name__,
                'title': community.title,
                'last_activity': str(community.content_modified),
                'url': route_url('archive_to_box', traverse=path.lstrip('/')),
                'items': count,
                'status': getattr(community, 'archive_status', None),
            }

        logger.info('arc2box: Got communities')
        return [record(community) for community in results()]

    @box_api_view(
        context=ICommunity,
        request_method='GET',
    )
    def community_status(self):
        """
        GET /arc2box/communities/<community>/

        Returns:

            {
                'status': null or string archive state (see above),
                'log': [
                    {'timestamp': timestamp of log entry,
                     'message': multiline string, log entry,
                     'level': logging level, one of 'debug', 'info', 'warn',
                              'error', 'critical'},
                    etc...
                ]
            }
        """
        # In later versions of Pyramid you can register a new JSON renderer
        # with an adapter for datetime objects.  That would be preferable to
        # doing this.
        community = self.context
        log = map(dict, getattr(community, 'archive_log', ()))
        for entry in log:
            entry['timestamp'] = entry['timestamp'].isoformat()

        logger.info('arc2box: Get loginfo for community: ' +
                  community.title)
        return {
            'status': getattr(community, 'archive_status', None),
            'log': log,
        }

    @box_api_view(
        context=ICommunity,
        request_method='PATCH',
        custom_predicates=(action('copy'),),
    )
    def copy(self):
        """
        PATCH /arc2box/communities/<community>/
        {"action": "copy"}

        Tell the archiver to start copying content from this community to box.
        The community must not already be in any archive state.  This operation
        will place the community in the 'copying' state.  The archiver  will
        place the community into the 'reviewing' state at the completion of the
        copy operation.

        Returns a status of '202 Accepted'.
        """
        community = self.context

        # For all but KarlAdmin, reduce access to VIEW only
        acl = []
        for allow, who, what in community.__acl__:
            if allow == Allow and who != 'group.KarlAdmin':
                what = (VIEW,)
            acl.append((allow, who, what))
        modify_acl(community, acl)

        # Queue the community for copying
        self.queue.queue_for_copy(community)
        community.archive_status = 'copying'

        logger.info('arc2box: copy community: ' + community.title)
        return HTTPAccepted()

    @box_api_view(
        context=ICommunity,
        request_method='PATCH',
        custom_predicates=(action('stop'),),
    )
    def stop(self):
        """
        PATCH /arc2box/communities/<community>/
        {"action": "stop"}

        Tell the archiver to stop copying content from this community to box
        and to take the community out of the 'copying' state.  The community
        must be in the 'copying' or 'reviewing' state.  The community will
        return to normal operation and will not be in any archiving state.
        """
        community = self.context
        status = getattr(community, 'archive_status', None)
        if status not in ('copying', 'reviewing', 'exception'):
            return HTTPBadRequest(
                "Community must be in 'copying' or 'reviewing' state.")

        # Restore normal ACL for workflow state
        wf = get_workflow(ICommunity, 'security', community)
        wf.reset(community)
        del community.__custom_acl__

        # If still in the copy queue, the archiver will skip this community
        del community.archive_status

        logger.info('arc2box: stop community: ' + community.title)
        return HTTPAccepted()

    @box_api_view(
        context=ICommunity,
        request_method='PATCH',
        custom_predicates=(action('mothball'),),
    )
    def mothball(self):
        """
        PATCH /arc2box/communities/<community>/
        {"action": "mothball"}

        Tell the archiver to remove all content from the community in Karl.
        This operation cannot be stopped or reversed. The community must be in
        the 'reviewing' state.  This operation will place the community into
        the 'removing' state.  The archiver will place the community into the
        'archived' state at the completion of the mothball operation.
        """
        community = self.context
        status = getattr(community, 'archive_status', None)
        if status != 'reviewing':
            return HTTPBadRequest(
                "Community must be in 'reviewing' state.")

        # Queue the community for mothball
        self.queue.queue_for_mothball(community)
        community.archive_status = 'removing'

        logger.info('arc2box: mothball community: ' + community.title)
        return HTTPAccepted()

# -*- coding: utf-8 -*-
# Copyright (C) 2014-2016 Taiga Agile LLC <support@taiga.io>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.utils.translation import ugettext as _
from django.conf import settings

from taiga.base.api import viewsets
from taiga.base import response
from taiga.base import exceptions as exc
from taiga.base.decorators import list_route
from taiga.users.models import AuthData, User
from taiga.users.services import get_user_photo_url
from taiga.users.gravatar import get_user_gravatar_id

from .normal import JiraNormalImporter
#from .agile import JiraAgileImporter
from . import permissions, tasks


class JiraImporterViewSet(viewsets.ViewSet):
    permission_classes = (permissions.ImporterPermission,)

    def _get_token(self, request):
        token_data = request.DATA.get('token', "").split(".")

        token = {
            "access_token": token_data[0],
            "access_token_secret": token_data[1],
            "key_cert": settings.JIRA_CERT,
            "consumer_key": settings.JIRA_CONSUMER_KEY
        }
        return token

    @list_route(methods=["POST"])
    def list_users(self, request, *args, **kwargs):
        self.check_permissions(request, "list_users", None)

        url = request.DATA.get('url', None)
        token = self._get_token(request)
        project_id = request.DATA.get('project', None)

        if not project_id:
            raise exc.WrongArguments(_("The project param is needed"))

        importer = JiraNormalImporter(request.user, url, token)
        users = importer.list_users(project_id)
        for user in users:
            user['user'] = None
            if not user['email']:
                continue

            try:
                taiga_user = User.objects.get(email=user['email'])
            except User.DoesNotExist:
                continue

            user['user'] = {
                'id': taiga_user.id,
                'full_name': taiga_user.get_full_name(),
                'gravatar_id': get_user_gravatar_id(taiga_user),
                'photo': get_user_photo_url(taiga_user),
            }
        return response.Ok(users)

    @list_route(methods=["POST"])
    def list_projects(self, request, *args, **kwargs):
        self.check_permissions(request, "list_projects", None)
        url = request.DATA.get('url', None)
        token = self._get_token(request)
        importer = JiraNormalImporter(request.user, url, token)
        projects = importer.list_projects()
        return response.Ok(projects)

    @list_route(methods=["POST"])
    def import_project(self, request, *args, **kwargs):
        self.check_permissions(request, "import_project", None)

        url = request.DATA.get('url', None)
        token = self._get_token(request)
        project_id = request.DATA.get('project', None)
        if not project_id:
            raise exc.WrongArguments(_("The project param is needed"))

        options = {
            "template": request.DATA.get('template', "kanban"),
            "users_bindings": request.DATA.get("users_bindings", {}),
            "keep_external_reference": request.DATA.get("keep_external_reference", False),
            "is_private": request.DATA.get("is_private", False),
        }

        if settings.CELERY_ENABLED:
            task = tasks.import_project.delay(request.user, token, project_id, options)
            return response.Accepted({"jira_import_id": task.id})

        importer = JiraNormalImporter(request.user, url, token)
        project = importer.import_project(project_id, options)
        project_data = {
            "slug": project.slug,
            "my_permissions": ["view_us"],
            "is_backlog_activated": project.is_backlog_activated,
            "is_kanban_activated": project.is_kanban_activated,
        }

        return response.Ok(project_data)

    @list_route(methods=["GET"])
    def auth_url(self, request, *args, **kwargs):
        self.check_permissions(request, "auth_url", None)
        jira_url = request.QUERY_PARAMS.get('url', None)

        if not jira_url:
            raise exc.WrongArguments(_("The url param is needed"))

        (oauth_token, oauth_secret, url) = JiraNormalImporter.get_auth_url(
            jira_url,
            settings.JIRA_CONSUMER_KEY,
            settings.JIRA_CERT,
            True
        )

        (auth_data, created) = AuthData.objects.get_or_create(
            user=request.user,
            key="jira-oauth",
            defaults={
                "value": "",
                "extra": {},
            }
        )
        auth_data.extra = {
            "oauth_token": oauth_token,
            "oauth_secret": oauth_secret,
            "url": jira_url,
        }
        auth_data.save()

        return response.Ok({"url": url})

    @list_route(methods=["POST"])
    def authorize(self, request, *args, **kwargs):
        self.check_permissions(request, "authorize", None)

        try:
            oauth_data = request.user.auth_data.get(key="jira-oauth")
            oauth_token = oauth_data.extra['oauth_token']
            oauth_secret = oauth_data.extra['oauth_secret']
            server_url = oauth_data.extra['url']
            oauth_data.delete()

            jira_token = JiraNormalImporter.get_access_token(
                server_url,
                settings.JIRA_CONSUMER_KEY,
                settings.JIRA_CERT,
                oauth_token,
                oauth_secret,
                True
            )
        except Exception as e:
            raise exc.WrongArguments(_("Invalid or expired auth token"))

        return response.Ok({
            "token": jira_token['access_token'] + "." + jira_token['access_token_secret'],
            "url": server_url
        })

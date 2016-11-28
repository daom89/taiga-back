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

from taiga.base.api import viewsets
from taiga.base import response
from taiga.base.decorators import list_route

from .importer import TrelloImporter
from . import permissions


class TrelloImporterViewSet(viewsets.ViewSet):
    permission_classes = (permissions.ImporterPermission,)

    @list_route(methods=["GET"])
    def list_users(self, request, *args, **kwargs):
        self.check_permissions(request, "list_users", None)

        token = request.QUERY_PARAMS.get('token')
        project_id = request.QUERY_PARAMS.get('project')
        importer = TrelloImporter(request.user, token)
        users = importer.list_users(project_id)
        return response.Ok(users)

    @list_route(methods=["GET"])
    def list_projects(self, request, *args, **kwargs):
        self.check_permissions(request, "list_projects", None)

        token = request.QUERY_PARAMS.get('token')
        importer = TrelloImporter(request.user, token)
        projects = importer.list_projects()
        return response.Ok(projects)

    @list_route(methods=["POST"])
    def import_project(self, request, *args, **kwargs):
        self.check_permissions(request, "import_project", None)

        token = request.QUERY_PARAMS.get('token')
        project_id = request.QUERY_PARAMS.get('project')
        options = None
        importer = TrelloImporter(request.user, token)
        project = importer.import_project(project_id)
        return response.Ok(project)


    @list_route(methods=["GET"])
    def auth_url(self, request, *args, **kwargs):
        self.check_permissions(request, "auth_url", None)

        (oauth_token, oauth_secret, url) = TrelloImporter.get_auth_url()
        return response.Ok({
            "oauth_token": oauth_token,
            "oauth_secret": oauth_secret,
            "url": url,
        })

    @list_route(methods=["POST"])
    def authorize(self, request, *args, **kwargs):
        oauth_token = request.QUERY_PARAMS.get('oauth_token')
        oauth_secret = request.QUERY_PARAMS.get('oauth_secret')
        oauth_verifier = request.QUERY_PARAMS.get('oauth_verifier')
        self.check_permissions(request, "authorize", None)

        return response.Ok({
            "token": TrelloImporter.get_access_token(oauth_token, oauth_secret, oauth_verifier)
        })

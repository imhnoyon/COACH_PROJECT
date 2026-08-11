import urllib.parse
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_string):
    """
    Validates a SimpleJWT access token and returns the corresponding active User.
    """
    if not token_string:
        return AnonymousUser()

    try:
        access_token = AccessToken(token_string)
        user_id = access_token.get('user_id')
        if not user_id:
            return AnonymousUser()
        return User.objects.get(id=user_id, is_active=True)
    except (InvalidToken, TokenError, User.DoesNotExist, Exception):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom Channels middleware that authenticates WebSocket connections
    using a SimpleJWT token passed via:
    1. Query parameters: ws://.../?token=<jwt_access_token>
    2. HTTP Headers: Authorization: Bearer <jwt_access_token>
    3. Sec-WebSocket-Protocol / Subprotocols
    """

    async def __call__(self, scope, receive, send):
        token = None

        # 1. Check Query String
        query_string = scope.get('query_string', b'').decode('utf-8')
        if query_string:
            query_params = urllib.parse.parse_qs(query_string)
            if 'token' in query_params:
                token = query_params['token'][0]

        # 2. Check Headers if not found in query string
        if not token and 'headers' in scope:
            headers = dict(scope['headers'])
            auth_header = headers.get(b'authorization', b'').decode('utf-8')
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ', 1)[1].strip()

        # 3. Check Subprotocols
        if not token and 'subprotocols' in scope:
            for protocol in scope.get('subprotocols', []):
                if protocol.startswith('token.'):
                    token = protocol.split('token.', 1)[1]
                    break

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Helper function to wrap an ASGI application with JWTAuthMiddleware.
    """
    return JWTAuthMiddleware(inner)

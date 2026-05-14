from django.db import connection
from django.core.cache import cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    
    """

    checks = {}

    # DB 確認
    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception:
        checks['database'] = 'error'

    # Redis 確認
    try:
        cache.set('health_check', '1', 5)
        checks['redis'] = 'ok'
    except Exception:
        checks['redis'] = 'error'

    all_ok = all(v == 'ok' for v in checks.values())
    return Response({'status': 'ok' if all_ok else 'degraded', 'checks': checks}, status=200 if all_ok else 503)


from rest_framework.views import exception_handler
from rest_framework import status

def custom_exception_handler(exc, context):
    """
    統一錯誤回應格式

    DRF的錯誤格式不統一:
       有時 {"detail":"..."}
       有時 {"field": []"..."]}
    
    統一成:
        {"success": false, "error": {"code": 400, "message": ...}}
    """

    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': response.data,
            }
        }

    return response
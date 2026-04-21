from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_detail = response.data

        if isinstance(error_detail, dict):
            first_key = next(iter(error_detail), None)
            first_msg = error_detail.get(first_key, ['Xatolik yuz berdi'])
            message = first_msg[0] if isinstance(first_msg, list) else str(first_msg)
        elif isinstance(error_detail, list):
            message = str(error_detail[0])
        else:
            message = str(error_detail)

        response.data = {
            'success': False,
            'error': {
                'code': _get_error_code(response.status_code),
                'message': message,
                'details': error_detail if response.status_code >= 400 else {},
            }
        }

    return response


def _get_error_code(status_code: int) -> str:
    codes = {
        400: 'BAD_REQUEST',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        422: 'VALIDATION_ERROR',
        500: 'INTERNAL_SERVER_ERROR',
    }
    return codes.get(status_code, 'ERROR')

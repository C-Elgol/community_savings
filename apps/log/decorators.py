import logging
import traceback
from functools import wraps
from django.http import JsonResponse, HttpRequest
from django.contrib import messages
from apps.log.models import ActivityLog, FunctionalErrorLog, LogSystemStatus

logger = logging.getLogger(__name__)

def log_activity_and_errors(action: str = None, module: str = None):
    """
    Decorator for views (both FBV and CBV methods like post())
    to automatically log successful completion to ActivityLog
    and unexpected exceptions to FunctionalErrorLog.
    """
    def decorator(view_func):
        _action = action
        _module = module
        
        if not _module and hasattr(view_func, '__module__'):
            parts = view_func.__module__.split('.')
            if len(parts) >= 2:
                _module = parts[1].capitalize()
            else:
                _module = "Unknown"
                
        if not _action and hasattr(view_func, '__qualname__'):
            import re
            name = view_func.__qualname__.replace('.post', '').replace('.dispatch', '').replace('.get', '')
            name = re.sub(r'(?<!^)(?=[A-Z])', ' ', name)
            _action = name
        elif not _action:
            _action = "System Action"

        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):
            # Extract HttpRequest object from arguments
            request = None
            for arg in args:
                if isinstance(arg, HttpRequest):
                    request = arg
                    break
            
            if not request and 'request' in kwargs:
                if isinstance(kwargs['request'], HttpRequest):
                    request = kwargs['request']

            # If it's a CBV and it has a 'request' attribute bound (some cases)
            if not request and len(args) > 0 and hasattr(args[0], 'request'):
                req = getattr(args[0], 'request')
                if isinstance(req, HttpRequest):
                    request = req

            try:
                # Execute original view
                response = view_func(*args, **kwargs)
                
                # For ActivityLog, we only want to log on success (HTTP 200, 201, 302)
                # Redirects (302) are common after a successful POST
                if hasattr(response, 'status_code') and response.status_code in [200, 201, 302, 204]:
                    user = getattr(request, 'user', None) if request else None
                    if user and not user.is_authenticated:
                        user = None

                    ActivityLog.log_action(
                        user=user,
                        action=_action,
                        module=_module,
                        status=LogSystemStatus.SUCCESS,
                        details=f"{_action} completed successfully.",
                        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else "",
                        metadata={'ip_address': request.META.get('REMOTE_ADDR') if request else ""}
                    )
                return response

            except Exception as e:
                # Handle error
                trace = traceback.format_exc()
                user = getattr(request, 'user', None) if request else None
                if user and not user.is_authenticated:
                    user = None

                input_data = str(request.POST.dict()) if request and hasattr(request, 'POST') else ""
                if 'password' in input_data.lower():
                    input_data = "HIDDEN DUE TO CONTAINING PASSWORD"

                if request:
                    ip_address = request.META.get('REMOTE_ADDR')
                    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
                else:
                    ip_address = None
                    is_ajax = False

                FunctionalErrorLog.log_error(
                    user=user,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    function_or_view=view_func.__name__,
                    input_data=input_data,
                    context=f"Unexpected error in {_action}",
                    traceback=trace,
                    metadata={'ip_address': ip_address}
                )
                logger.error(f"Error in {_action} (Module: {_module}): {e}\n{trace}")
                
                error_message = "An unexpected error occurred. Please try again later."
                if is_ajax:
                    return JsonResponse({"success": False, "message": error_message}, status=500)
                
                if request:
                    messages.error(request, error_message)
                
                # Re-raise so Django can handle the 500 error page if not ajax
                raise e

        return _wrapped_view
    return decorator

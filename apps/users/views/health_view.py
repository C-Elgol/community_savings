from django.http import JsonResponse

def health(request):
    """
    Health check endpoint for blue-green deployment.
    """
    return JsonResponse({"status": "ok"})

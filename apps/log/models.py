from __future__ import annotations
from typing import Optional, Union

from django.db import models
from django.db.models import QuerySet

from apps.users.models import SavingsBaseModel, User
from apps.global_data.enum import LogSystemStatus


class ActivityLog(SavingsBaseModel):
    """
    Model representing a log of user/system actions in the application.
    author: ayemeleelgol@gmail.com
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    action = models.CharField(max_length=255)
    module = models.CharField(max_length=100)
    details = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=LogSystemStatus.choices, default=LogSystemStatus.SUCCESS)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=["module", "created"]),
            models.Index(fields=["status", "created"]),
            models.Index(fields=["ip_address"]),
        ]

    def __str__(self) -> str:
        return f"{self.created} - {self.user} - {self.action} ({self.status})"

    @classmethod
    def log_action(
        cls,
        user: Optional[User],
        action: str,
        module: str,
        status: str = LogSystemStatus.SUCCESS,
        details: str = "",
        user_agent: str = "",
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> "ActivityLog":
        return cls.objects.create(
            user=user,
            action=action,
            module=module,
            status=status,
            details=details,
            user_agent=user_agent,
            ip_address=ip_address,
            metadata=metadata or {},  # uses BaseModel metadata
        )

    @classmethod
    def get_logs(cls, limit: Optional[int] = None) -> QuerySet["ActivityLog"]:
        qs = cls.objects.all()
        return qs[:limit] if limit else qs

    @classmethod
    def get_by_id(cls, log_id: Union[str, int]) -> Optional["ActivityLog"]:
        return cls.objects.filter(id=log_id).first()

    @classmethod
    def delete_by_id(cls, log_id: Union[str, int]) -> int:
        return cls.all_objects.filter(id=log_id).delete()[0]


class FunctionalErrorLog(SavingsBaseModel):
    """
    Model representing a log of functional errors in the application.
    author: ayemeleelgol@gmail.com    
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="error_logs")

    error_type = models.CharField(max_length=100)
    error_message = models.TextField()
    function_or_view = models.CharField(max_length=255)

    input_data = models.TextField(blank=True)
    context = models.TextField(blank=True)
    traceback = models.TextField(blank=True)

    is_resolved = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = "Functional Error"
        verbose_name_plural = "Functional Errors"
        indexes = [
            models.Index(fields=["is_resolved", "created"]),
            models.Index(fields=["error_type", "created"]),
            models.Index(fields=["ip_address"]),
        ]

    def __str__(self) -> str:
        return f"{self.created:%Y-%m-%d %H:%M:%S} - {self.error_type} - {self.function_or_view}"

    @classmethod
    def log_error(
        cls,
        user: Optional[User],
        error_type: str,
        error_message: str,
        function_or_view: str,
        input_data: str = "",
        context: str = "",
        traceback: str = "",
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None,
        is_resolved: bool = False,
    ) -> "FunctionalErrorLog":
        return cls.objects.create(
            user=user,
            error_type=error_type,
            error_message=error_message,
            function_or_view=function_or_view,
            input_data=input_data,
            context=context,
            traceback=traceback,
            ip_address=ip_address,
            metadata=metadata or {},  # uses BaseModel metadata
            is_resolved=is_resolved,
        )

    @classmethod
    def get_errors(cls, limit: Optional[int] = None) -> QuerySet["FunctionalErrorLog"]:
        qs = cls.objects.all()
        return qs[:limit] if limit else qs

    @classmethod
    def get_by_id(cls, error_id: Union[str, int]) -> Optional["FunctionalErrorLog"]:
        return cls.objects.filter(id=error_id).first()

    @classmethod
    def delete_by_id(cls, error_id: Union[str, int]) -> int:
        return cls.all_objects.filter(id=error_id).delete()[0]
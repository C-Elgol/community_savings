import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel, ActivatorModel
from phonenumber_field.modelfields import PhoneNumberField

from .managers import UserManager


class SavingsQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SavingsManager(models.Manager):
    """
    Default manager hides soft-deleted rows.
    author: ayemeleelgol@gmail.com    
    """
    def get_queryset(self):
        return SavingsQuerySet(self.model, using=self._db).alive()

    def all_with_deleted(self):
        return SavingsQuerySet(self.model, using=self._db)

    def only_deleted(self):
        return self.all_with_deleted().deleted()


class SavingsBaseModel(TimeStampedModel, ActivatorModel):
    """
    Base model for the entire system:
    - UUID primary key
    - created/modified from TimeStampedModel
    - is_active from ActivatorModel
    - soft delete
    - metadata json
    author: ayemeleelgol@gmail.com    
    """
    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
        editable=False,
        unique=True,
        help_text=_("Unique UUID identifier for the record."),
    )
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Soft delete flag."),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Additional metadata in JSON format."),
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address associated with the record creation or update.")
    )
    objects = SavingsManager()
    all_objects = models.Manager()  # includes deleted

    class Meta:
        abstract = True

    def soft_delete(self, save=True):
        self.is_deleted = True
        if save:
            self.save(update_fields=["is_deleted", "modified"])

    def __str__(self):
        return str(self.id)


class User(SavingsBaseModel, PermissionsMixin, AbstractBaseUser):
    """
    Name: User
    Description: Custom user model with email as the unique identifier and role-based flags.
    Author: ayemeleelgol@gmail.com
    """
    email = models.EmailField(
        _("email address"),
        blank=False,
        null=False,
        unique=True,
        error_messages={"unique": _("A user with that email already exists.")}
    )
    fullname = models.CharField(max_length=100, null=True, blank=True, help_text=_("Full name of the user."))
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the admin site.")
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active. Unselect instead of deleting accounts.")
    )
    is_superuser = models.BooleanField(
        _("superuser status"),
        default=False,
        help_text=_("Designates that this user has all permissions without explicitly assigning them.")
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    # Role-based fields
    is_auditor = models.BooleanField(
        _("is auditor"), 
        default=False, 
        help_text=_("User is an auditor.")
    )
    is_admin = models.BooleanField(
        _("is admin"), 
        default=False, 
        help_text=_("User is an admin.")
    )
    is_manually_deleted = models.BooleanField(
        _("is manually deleted"),
        default=False,
        help_text=_("Marks if the user was manually deleted.")
    )

    # New field for terms acceptance
    has_accepted_terms = models.BooleanField(
        _("has accepted terms"),
        default=False,
        help_text=_("Indicates whether the user has accepted the Terms of Service and Privacy Policy during registration.")
    )

    # New field for profile picture
    profile_picture = models.ImageField(
        verbose_name=_("Profile Picture"),
        null=True,
        blank=True,
        upload_to="profile/",
        help_text=_("User's profile picture.")
    )


    # Authentication settings
    username = None
    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")

    def has_perm(self, perm, obj=None):
        """Check if the user has a specific permission."""
        return True  # Simplified for superusers; adjust based on your needs

    def clean(self):
        """Normalize email before saving."""
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    @property
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.fullname

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split("@")[0]

    def __str__(self):
        return self.email

    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return None


class Profile(SavingsBaseModel):
    """
    Name: Profile
    Description: Stores user profile information for physical product delivery.
    Author: ayemeleelgol@gmail.com
    """
    user = models.OneToOneField(
        'User',
        on_delete=models.PROTECT,
        related_name='profile',
        help_text=_("Associated user account.")
    )
    country = models.CharField(_("Country"), max_length=50, blank=True)
    region = models.CharField(_("Region"), max_length=50, default="Cameroon", blank=True)
    city = models.CharField(_("City"), max_length=50, blank=True)
    address = models.CharField(_("Address"), max_length=100, blank=True)
    zip_code = models.CharField(_("Zip Code"), max_length=20, default="00000", blank=True)

    class Meta:
        verbose_name = _("Profile")
        verbose_name_plural = _("Profiles")

    def __str__(self):
        return f"{self.user.email}'s Profile"


def partner_logo_path(instance, filename):
    """Generate file path for partner logos."""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return f'partners/logos/{filename}'


class Partners(SavingsBaseModel):
    """
    class: Partners
    Description: Stores information about business partners or collaborators.
    Author: ayemeleelgol@gmail.com
    """
    name = models.CharField(
        _("Name"),
        max_length=255,
        unique=True,
        help_text=_("Name of the partner organization.")
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text=_("URL-friendly identifier for the partner.")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Description of the partner organization.")
    )
    logo = models.ImageField(
        _("Logo"),
        upload_to=partner_logo_path,
        max_length=1000,
        null=True,
        blank=True,
        help_text=_("Partner's logo image.")
    )
    website = models.URLField(
        _("Website"),
        blank=True,
        null=True,
        help_text=_("Partner's website URL.")
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Indicates whether the partner is actively displayed.")
    )

    class Meta:
        verbose_name = _('Partner')
        verbose_name_plural = _('Partners')
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_deleted']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
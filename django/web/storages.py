from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class FranchiseEnquiryStorage(FileSystemStorage):
    """Django filesystem storage rooted outside the site's public MEDIA_ROOT."""

    @property
    def base_location(self):
        return self._location or settings.PRIVATE_MEDIA_ROOT

    @base_location.setter
    def base_location(self, value):
        self._location = value

    def url(self, name):
        raise ValueError("Franchise enquiry attachments require an authorized view.")

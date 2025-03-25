from django.db import models
from django.conf import settings


class PDFFile(models.Model):
    name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="frg/", storage=settings.DEFAULT_FILE_STORAGE
    )  # S3 storage
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def file_url(self):
        """Returns the S3 URL of the file."""
        return self.file.url

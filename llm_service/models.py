from django.db import models


class LLMUsage(models.Model):
	model_name = models.CharField(max_length=100)
	api_key_fingerprint = models.CharField(max_length=64)
	date = models.DateField()
	count = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		unique_together = ("model_name", "api_key_fingerprint", "date")
		indexes = [
			models.Index(fields=["model_name", "date"]),
			models.Index(fields=["api_key_fingerprint", "date"]),
		]

	def __str__(self) -> str:  # pragma: no cover - debug helper
		return f"{self.model_name} ({self.api_key_fingerprint}) {self.date}: {self.count}"

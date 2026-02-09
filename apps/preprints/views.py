from django.views.generic import ListView

from .models import Preprint


class PreprintListView(ListView):
    """Display all preprints, grouped by year."""
    model = Preprint
    template_name = "preprints/preprint_list.html"
    context_object_name = "preprints"
    paginate_by = 50

    def get_queryset(self):
        return Preprint.objects.published()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get available years for filtering
        context["years"] = (
            Preprint.objects.values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )
        return context


class PreprintYearView(ListView):
    """Display preprints for a specific year."""
    model = Preprint
    template_name = "preprints/preprint_year.html"
    context_object_name = "preprints"

    def get_queryset(self):
        return Preprint.objects.by_year(self.kwargs["year"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["year"] = self.kwargs["year"]
        context["years"] = (
            Preprint.objects.values_list("year", flat=True)
            .distinct()
            .order_by("-year")
        )
        return context

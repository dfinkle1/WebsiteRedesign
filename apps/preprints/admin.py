import re

from django.contrib import admin
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.html import format_html

from .models import Preprint


@admin.register(Preprint)
class PreprintAdmin(admin.ModelAdmin):
    list_display = ["entry_id_display", "title_display", "authors_short", "program_type", "created_at"]
    list_filter = ["year", "program_type"]
    search_fields = ["title", "authors", "arxiv_id", "program_code"]
    ordering = ["-year", "-sequence"]
    change_list_template = "admin/preprints/preprint_changelist.html"

    fieldsets = [
        ("Entry", {
            "fields": ["year", "sequence", "title", "authors"]
        }),
        ("Link", {
            "fields": ["arxiv_id", "url"],
            "description": "Provide either an arXiv ID or a custom URL"
        }),
        ("Program Info (not displayed publicly)", {
            "fields": ["program_type", "program_code", "aim_thanks_page"],
            "classes": ["collapse"]
        }),
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import/", self.admin_site.admin_view(self.import_view), name="preprints_preprint_import"),
        ]
        return custom_urls + urls

    def import_view(self, request):
        if request.method == "POST":
            text_content = request.POST.get("text_content", "")
            if text_content:
                created, updated, errors = self.parse_and_import(text_content)
                if created or updated:
                    messages.success(request, f"Imported {created} new preprints, updated {updated} existing.")
                if errors:
                    messages.warning(request, f"{len(errors)} entries had errors.")
                return redirect("admin:preprints_preprint_changelist")

        return render(request, "admin/preprints/import_form.html", {
            "title": "Import Preprints",
            "opts": self.model._meta,
        })

    def parse_and_import(self, content):
        """Parse text content and import preprints."""
        created = 0
        updated = 0
        errors = []

        blocks = re.split(r"\n\s*\n", content)

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Skip volume headers
            if re.match(r"Volume\s+\d+,\s+\d{4}", block):
                continue

            entry = self.parse_entry(block)
            if entry:
                try:
                    obj, was_created = Preprint.objects.update_or_create(
                        year=entry["year"],
                        sequence=entry["sequence"],
                        defaults={
                            "title": entry["title"],
                            "authors": entry["authors"],
                            "arxiv_id": entry.get("arxiv_id", ""),
                            "url": entry.get("url", ""),
                            "program_type": entry.get("program_type", ""),
                            "program_code": entry.get("program_code", ""),
                            "aim_thanks_page": entry.get("aim_thanks_page"),
                        },
                    )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except Exception as e:
                    errors.append(str(e))

        return created, updated, errors

    def parse_entry(self, block):
        """Parse a single entry block."""
        lines = [line.strip() for line in block.split("\n") if line.strip()]

        if len(lines) < 3:
            return None

        # First line should be entry ID like "2026-5"
        entry_match = re.match(r"(\d{4})-(\d+)", lines[0])
        if not entry_match:
            return None

        year = int(entry_match.group(1))
        sequence = int(entry_match.group(2))

        # Second line is arxiv ID or URL
        arxiv_id = ""
        url = ""
        link_line = lines[1]

        if link_line.startswith("http"):
            url = link_line
        elif re.match(r"^\d{4}\.\d{4,5}", link_line):
            # New format: 2601.11912
            arxiv_id = link_line.split()[0]
        elif re.match(r"^\d{7}", link_line):
            # Old format number only: 0609210
            arxiv_id = link_line.split()[0]
        elif re.match(r"^[a-z-]+(\.[A-Z]{2})?/\d+", link_line, re.I):
            # Old format with subject: math.NT/0609210, math-ph/0512023, hep-th/9901001
            arxiv_id = link_line.split()[0]

        # Third line is title
        title = lines[2] if len(lines) > 2 else ""

        # Fourth line is authors
        authors = lines[3] if len(lines) > 3 else ""

        # Parse remaining lines for program info and AIM thanks
        program_type = ""
        program_code = ""
        aim_thanks_page = None

        for line in lines[4:]:
            program_match = re.match(r"\((?:SQuaRE|Square|square)\s+(\d+)\)", line, re.I)
            if program_match:
                program_type = "square"
                program_code = program_match.group(1)
                continue

            program_match = re.match(r"\((?:Workshop|Workshops|workshop)\s+(\d+)\)", line, re.I)
            if program_match:
                program_type = "workshop"
                program_code = program_match.group(1)
                continue

            program_match = re.match(r"\(ARC\s+(\d+)\)", line, re.I)
            if program_match:
                program_type = "arc"
                program_code = program_match.group(1)
                continue

            program_match = re.match(r"\(REUF\s+(\d+)\)", line, re.I)
            if program_match:
                program_type = "reuf"
                program_code = program_match.group(1)
                continue

            if re.match(r"\(AIM\s+(?:Staff|staff)\)", line, re.I):
                program_type = "other"
                program_code = "staff"
                continue

            thanks_match = re.search(r"\(AIM thanks[,\s]+p\.?\s*(\d+)", line, re.I)
            if thanks_match:
                aim_thanks_page = int(thanks_match.group(1))
                continue

        return {
            "year": year,
            "sequence": sequence,
            "title": title,
            "authors": authors,
            "arxiv_id": arxiv_id,
            "url": url,
            "program_type": program_type,
            "program_code": program_code,
            "aim_thanks_page": aim_thanks_page,
        }

    @admin.display(description="Entry ID", ordering="year")
    def entry_id_display(self, obj):
        return obj.entry_id

    @admin.display(description="Title")
    def title_display(self, obj):
        title = obj.title[:60] + "..." if len(obj.title) > 60 else obj.title
        if obj.paper_url:
            return format_html('<a href="{url}" target="_blank">{title}</a>', url=obj.paper_url, title=title)
        return title

    @admin.display(description="Authors")
    def authors_short(self, obj):
        authors = obj.authors_list
        if len(authors) <= 2:
            return obj.authors
        return f"{authors[0]} et al. ({len(authors)} authors)"

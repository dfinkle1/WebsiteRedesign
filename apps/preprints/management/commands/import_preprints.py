"""
Import preprints from the legacy text file format.

Usage:
    python manage.py import_preprints /path/to/preprints.txt
    python manage.py import_preprints /path/to/preprints.txt --dry-run
"""
import re
from django.core.management.base import BaseCommand
from apps.preprints.models import Preprint


class Command(BaseCommand):
    help = "Import preprints from a legacy text file"

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path to the preprints text file")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate without saving to database",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing preprints before importing",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        dry_run = options["dry_run"]
        clear = options["clear"]

        if clear and not dry_run:
            count = Preprint.objects.count()
            Preprint.objects.all().delete()
            self.stdout.write(f"Cleared {count} existing preprints")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        entries = self.parse_file(content)

        created = 0
        skipped = 0
        errors = []

        for entry in entries:
            try:
                if dry_run:
                    self.stdout.write(
                        f"  Would create: {entry['year']}-{entry['sequence']} - {entry['title'][:50]}..."
                    )
                    created += 1
                else:
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
                        skipped += 1
            except Exception as e:
                errors.append(f"{entry.get('entry_id', 'unknown')}: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would create' if dry_run else 'Created'}: {created}, "
                f"{'Would skip' if dry_run else 'Updated'}: {skipped}"
            )
        )

        if errors:
            self.stdout.write(self.style.ERROR(f"Errors: {len(errors)}"))
            for error in errors[:10]:
                self.stdout.write(f"  {error}")

    def parse_file(self, content):
        """Parse the preprints text file into a list of entry dictionaries."""
        entries = []

        # Split into blocks by double newlines
        blocks = re.split(r"\n\s*\n", content)

        current_year = None

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Check for volume header
            volume_match = re.match(r"Volume\s+\d+,\s+(\d{4})", block)
            if volume_match:
                current_year = int(volume_match.group(1))
                continue

            # Try to parse as an entry
            entry = self.parse_entry(block, current_year)
            if entry:
                entries.append(entry)

        return entries

    def parse_entry(self, block, fallback_year):
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
            # Program info: (SQuaRE 1269), (Workshop 1101), (AIM Staff), (ARC 965), (REUF xxx)
            program_match = re.match(
                r"\((?:SQuaRE|Square|square|SQUARE)\s+(\d+)\)", line, re.I
            )
            if program_match:
                program_type = "square"
                program_code = program_match.group(1)
                continue

            program_match = re.match(
                r"\((?:Workshop|Workshops|workshop)\s+(\d+)\)", line, re.I
            )
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

            # AIM thanks page
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

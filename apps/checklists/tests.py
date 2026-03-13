from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from programs.models import Program
from .models import ChecklistTemplate, ChecklistTemplateItem, ProgramChecklist, ProgramChecklistItem
from .services import apply_template_to_program

User = get_user_model()


class ChecklistTemplateTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.template = ChecklistTemplate.objects.create(
            name="Workshop Template",
            program_type="WORKSHOP",
            created_by=self.staff,
        )
        ChecklistTemplateItem.objects.create(
            template=self.template, title="Book venue", order=1,
            category="pre_program", default_days_before_start=-30,
        )
        ChecklistTemplateItem.objects.create(
            template=self.template, title="Send invites", order=2,
            category="pre_program", default_days_before_start=-14,
        )
        ChecklistTemplateItem.objects.create(
            template=self.template, title="Send follow-up", order=3,
            category="post_program", default_days_before_start=7,
        )

    def test_template_item_count(self):
        self.assertEqual(self.template.item_count(), 3)

    def test_template_str(self):
        self.assertIn("Workshop Template", str(self.template))


class ApplyTemplateServiceTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.template = ChecklistTemplate.objects.create(
            name="Workshop Template",
            program_type="WORKSHOP",
            created_by=self.staff,
        )
        ChecklistTemplateItem.objects.create(
            template=self.template, title="Book venue", order=1,
            category="pre_program", default_days_before_start=-30,
        )
        ChecklistTemplateItem.objects.create(
            template=self.template, title="Send follow-up", order=2,
            category="post_program", default_days_before_start=7,
        )
        self.program = Program.objects.create(
            title="Test Workshop",
            type=Program.ProgramType.WORKSHOP,
            code=9999,
            start_date=date.today() + timedelta(days=60),
        )

    def test_apply_creates_checklist(self):
        checklist = apply_template_to_program(self.program, self.template, self.staff)
        self.assertIsInstance(checklist, ProgramChecklist)
        self.assertEqual(checklist.program, self.program)
        self.assertEqual(checklist.items.count(), 2)

    def test_due_dates_calculated_from_start(self):
        checklist = apply_template_to_program(self.program, self.template, self.staff)
        item = checklist.items.get(title="Book venue")
        expected = self.program.start_date + timedelta(days=-30)
        self.assertEqual(item.due_date, expected)

    def test_post_program_due_date(self):
        checklist = apply_template_to_program(self.program, self.template, self.staff)
        item = checklist.items.get(title="Send follow-up")
        expected = self.program.start_date + timedelta(days=7)
        self.assertEqual(item.due_date, expected)

    def test_cannot_apply_twice(self):
        apply_template_to_program(self.program, self.template, self.staff)
        with self.assertRaises(ValueError):
            apply_template_to_program(self.program, self.template, self.staff)

    def test_titles_copied_not_referenced(self):
        checklist = apply_template_to_program(self.program, self.template, self.staff)
        item = checklist.items.get(title="Book venue")
        # Changing template item title should NOT change the live item
        template_item = self.template.items.get(title="Book venue")
        template_item.title = "Changed title"
        template_item.save()
        item.refresh_from_db()
        self.assertEqual(item.title, "Book venue")  # still the original


class ProgramChecklistItemTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.program = Program.objects.create(
            title="Test Workshop", type=Program.ProgramType.WORKSHOP,
            code=9998, start_date=date.today() + timedelta(days=30),
        )
        self.checklist = ProgramChecklist.objects.create(
            program=self.program, created_by=self.staff
        )

    def _make_item(self, **kwargs):
        defaults = dict(
            checklist=self.checklist, title="Test task",
            category="pre_program", status="not_started",
        )
        defaults.update(kwargs)
        return ProgramChecklistItem.objects.create(**defaults)

    def test_is_overdue_true(self):
        item = self._make_item(due_date=date.today() - timedelta(days=1))
        self.assertTrue(item.is_overdue)

    def test_is_overdue_false_when_done(self):
        item = self._make_item(due_date=date.today() - timedelta(days=1), status="done")
        self.assertFalse(item.is_overdue)

    def test_is_overdue_false_when_future(self):
        item = self._make_item(due_date=date.today() + timedelta(days=5))
        self.assertFalse(item.is_overdue)

    def test_completion_stamps_timestamp(self):
        item = self._make_item()
        self.assertIsNone(item.completed_at)
        item.status = "done"
        item.save()
        self.assertIsNotNone(item.completed_at)

    def test_uncomplete_clears_timestamp(self):
        item = self._make_item(status="done")
        item.status = "in_progress"
        item.save()
        self.assertIsNone(item.completed_at)

    def test_urgency_class_overdue(self):
        item = self._make_item(due_date=date.today() - timedelta(days=1))
        self.assertEqual(item.urgency_class, "urgency-overdue")

    def test_urgency_class_ok(self):
        item = self._make_item(due_date=date.today() + timedelta(days=14))
        self.assertEqual(item.urgency_class, "urgency-ok")


class CompletionSummaryTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.program = Program.objects.create(
            title="Test Workshop", type=Program.ProgramType.WORKSHOP,
            code=9997, start_date=date.today() + timedelta(days=30),
        )
        self.checklist = ProgramChecklist.objects.create(
            program=self.program, created_by=self.staff
        )

    def _make_item(self, status="not_started", category="pre_program"):
        return ProgramChecklistItem.objects.create(
            checklist=self.checklist, title="Task", category=category, status=status,
        )

    def test_completion_pct(self):
        self._make_item(status="done")
        self._make_item(status="not_started")
        self._make_item(status="not_started")
        self._make_item(status="not_started")
        summary = self.checklist.completion_summary()
        self.assertEqual(summary["done"], 1)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["pct"], 25)

    def test_empty_checklist(self):
        summary = self.checklist.completion_summary()
        self.assertEqual(summary["pct"], 0)
        self.assertEqual(summary["total"], 0)


class SyncFromTemplateTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="pass", is_staff=True)
        self.template = ChecklistTemplate.objects.create(
            name="Workshop Template", program_type="WORKSHOP", created_by=self.staff
        )
        self.ti1 = ChecklistTemplateItem.objects.create(
            template=self.template, title="Task A", order=1, category="pre_program",
        )
        self.ti2 = ChecklistTemplateItem.objects.create(
            template=self.template, title="Task B", order=2, category="pre_program",
        )
        self.program = Program.objects.create(
            title="Test Workshop", type=Program.ProgramType.WORKSHOP,
            code=9995, start_date=date.today() + timedelta(days=30),
        )
        self.checklist = ProgramChecklist.objects.create(
            program=self.program, template_used=self.template, created_by=self.staff
        )
        # Manually create only Task A — simulates checklist applied before Task B was added
        ProgramChecklistItem.objects.create(
            checklist=self.checklist, template_item=self.ti1,
            title=self.ti1.title, category=self.ti1.category, order=self.ti1.order,
        )

    def test_sync_adds_missing_item(self):
        added = self.checklist.sync_from_template()
        self.assertEqual(added, 1)
        self.assertEqual(self.checklist.items.count(), 2)
        self.assertTrue(self.checklist.items.filter(title="Task B").exists())

    def test_sync_does_not_duplicate_existing(self):
        self.checklist.sync_from_template()
        self.checklist.sync_from_template()  # run twice
        self.assertEqual(self.checklist.items.count(), 2)

    def test_sync_no_template_returns_zero(self):
        self.checklist.template_used = None
        self.checklist.save()
        added = self.checklist.sync_from_template()
        self.assertEqual(added, 0)


class ChecklistViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff = User.objects.create_user(
            username="staff", password="pass", is_staff=True
        )
        self.program = Program.objects.create(
            title="Test Workshop", type=Program.ProgramType.WORKSHOP,
            code=9996, start_date=date.today() + timedelta(days=30),
        )
        self.template = ChecklistTemplate.objects.create(
            name="Workshop Template", program_type="WORKSHOP", created_by=self.staff
        )
        ChecklistTemplateItem.objects.create(
            template=self.template, title="Task 1", order=1,
            category="pre_program", default_days_before_start=-14,
        )

    def test_program_checklist_requires_staff(self):
        url = reverse("checklists:program_checklist", args=[self.program.code])
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_program_checklist_no_checklist_shows_form(self):
        self.client.login(username="staff", password="pass")
        url = reverse("checklists:program_checklist", args=[self.program.code])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Apply Template")

    def test_apply_template_via_post(self):
        self.client.login(username="staff", password="pass")
        url = reverse("checklists:program_checklist", args=[self.program.code])
        response = self.client.post(url, {
            "apply_template": "1",
            "template": self.template.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ProgramChecklist.objects.filter(program=self.program).exists())

    def test_hub_requires_staff(self):
        url = reverse("checklists:hub")
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

    def test_hub_loads_for_staff(self):
        self.client.login(username="staff", password="pass")
        url = reverse("checklists:hub")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_my_tasks_requires_login(self):
        url = reverse("checklists:my_tasks")
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

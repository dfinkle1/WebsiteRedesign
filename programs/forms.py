import re
from django import forms


class SendReminderForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'cols': 80, 'class': 'vLargeTextField'}),
        help_text="This message will be sent to all pending applicants.",
        initial="Please respond to your application for this program."
    )
    confirm = forms.BooleanField(
        required=True,
        label="I confirm I want to send these emails",
        help_text="You must check this box to proceed with sending emails."
    )


class BulkInviteForm(forms.Form):
    """Form for bulk inviting participants by email."""

    emails = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'cols': 80,
            'class': 'vLargeTextField',
            'placeholder': 'Enter email addresses separated by commas, semicolons, or new lines...\n\nexample1@university.edu, example2@college.edu\nexample3@institute.org'
        }),
        help_text="Paste email addresses separated by commas, semicolons, or new lines.",
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'cols': 80,
            'class': 'vLargeTextField',
            'placeholder': 'Optional personal message to include in invitation emails...'
        }),
        help_text="Optional message to include in all invitation emails.",
    )
    send_emails = forms.BooleanField(
        required=False,
        initial=True,
        label="Send invitation emails immediately",
        help_text="If unchecked, invitations will be created but emails won't be sent yet."
    )

    def clean_emails(self):
        """Parse and validate email addresses."""
        raw = self.cleaned_data['emails']

        # Split by comma, semicolon, or newline
        parts = re.split(r'[,;\n\r]+', raw)

        # Clean and validate each email
        emails = []
        invalid = []

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        for part in parts:
            email = part.strip().lower()
            if not email:
                continue

            if email_pattern.match(email):
                if email not in emails:  # Deduplicate
                    emails.append(email)
            else:
                invalid.append(part.strip())

        if invalid:
            raise forms.ValidationError(
                f"Invalid email addresses: {', '.join(invalid[:5])}"
                + (f" and {len(invalid) - 5} more..." if len(invalid) > 5 else "")
            )

        if not emails:
            raise forms.ValidationError("No valid email addresses found.")

        return emails

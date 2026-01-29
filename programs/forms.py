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

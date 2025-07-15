from django import forms


class EmailParticipantsForm(forms.Form):
    subject = forms.CharField(max_length=255, label="Email Subject")
    message = forms.CharField(widget=forms.Textarea, label="Email Message")

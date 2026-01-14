from django import forms
from people.models import People


class ProfileEditForm(forms.ModelForm):
    """Form for editing user profile information"""

    class Meta:
        model = People
        fields = [
            'first_name',
            'last_name',
            'preferred_name',
            'email_address',
            'phone_number',
            'institution',
            'mailing_address',
            'home_page',
            'dietary_restrictions',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'preferred_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Preferred Name'}),
            'email_address': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'institution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Institution'}),
            'mailing_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mailing Address'}),
            'home_page': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Homepage URL'}),
            'dietary_restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Dietary Restrictions'}),
        }
        labels = {
            'email_address': 'Email',
            'phone_number': 'Phone Number',
            'home_page': 'Homepage',
        }

    def clean_email_address(self):
        """Validate email address is unique"""
        email = self.cleaned_data.get('email_address')
        if email:
            # Check if email exists for another person
            existing = People.objects.filter(email_address__iexact=email).exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError('This email address is already in use.')
        return email.lower() if email else email

    def clean_home_page(self):
        """Ensure home page URL starts with http:// or https://"""
        url = self.cleaned_data.get('home_page')
        if url and not url.startswith(('http://', 'https://')):
            return f'https://{url}'
        return url

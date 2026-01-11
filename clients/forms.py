from django import forms
from .models import Client

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "first_name", "last_name", "email", "phone_number", 
            "dni", "birth_date", "gender", "address", 
            "status", "photo", "access_code", "tags", "groups"
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "last_name": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "email": forms.EmailInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "phone_number": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "dni": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "birth_date": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "gender": forms.Select(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900"}),
            "address": forms.Textarea(attrs={"rows": 2, "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "status": forms.Select(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900"}),
            "photo": forms.FileInput(attrs={"class": "w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100"}),
            "access_code": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400", "placeholder": "PIN de acceso"}),
            "tags": forms.CheckboxSelectMultiple(),
            "groups": forms.CheckboxSelectMultiple(),
        }

from .models import ClientNote, ClientDocument

class ClientNoteForm(forms.ModelForm):
    class Meta:
        model = ClientNote
        fields = ["text", "type", "is_popup"]
        widgets = {
            "text": forms.Textarea(attrs={"rows": 2, "placeholder": "Escribe una nota...", "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400 mb-2"}),
            "type": forms.Select(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 mb-2"}),
            "is_popup": forms.CheckboxInput(attrs={"class": "w-4 h-4 text-slate-900 bg-slate-100 border-slate-300 rounded focus:ring-slate-900"}),
        }

class ClientDocumentForm(forms.ModelForm):
    class Meta:
        model = ClientDocument
        fields = ["name", "file", "is_signed", "signed_at"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
            "file": forms.FileInput(attrs={"class": "w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100"}),
            "is_signed": forms.CheckboxInput(attrs={"class": "w-4 h-4 text-slate-900 bg-slate-100 border-slate-300 rounded focus:ring-slate-900"}),
            "signed_at": forms.DateInput(attrs={"type": "date", "class": "w-full rounded-xl border-slate-200 text-sm focus:ring-slate-900 focus:border-slate-900 placeholder-slate-400"}),
        }

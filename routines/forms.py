from django import forms
from .models import Exercise, ExerciseTag

class ExerciseForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False, 
        label="Etiquetas",
        help_text="Separa las etiquetas con comas (Ej: Fuerza, En casa, Sin material)"
    )

    class Meta:
        model = Exercise
        fields = ['name', 'description', 'muscle_group', 'video_url', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input w-full'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3}),
            'muscle_group': forms.Select(attrs={'class': 'form-select w-full'}),
            'video_url': forms.URLInput(attrs={'class': 'form-input w-full', 'placeholder': 'https://youtube.com/...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-indigo-600'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-populate tags
            self.fields['tags_input'].initial = ", ".join([t.name for t in self.instance.tags.all()])

    def save(self, commit=True, gym=None):
        exercise = super().save(commit=False)
        if gym:
            exercise.gym = gym
        
        if commit:
            exercise.save()
            self._save_tags(exercise, gym)
        return exercise

    def _save_tags(self, exercise, gym):
        tags_str = self.cleaned_data.get('tags_input', '')
        if not tags_str:
            exercise.tags.clear()
            return
        
        tag_names = [t.strip() for t in tags_str.split(',') if t.strip()]
        tags = []
        for name in tag_names:
            # Create tag if not exists for this gym
            tag, _ = ExerciseTag.objects.get_or_create(
                gym=gym, 
                name__iexact=name,
                defaults={'name': name}
            )
            tags.append(tag)
        
        exercise.tags.set(tags)

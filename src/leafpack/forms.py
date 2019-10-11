from django import forms
from .models import LeafPack, LeafPackType, Macroinvertebrate, LeafPackBug, LeafPackSensitivityGroup
from dataloaderinterface.models import SiteRegistration
from django.core.exceptions import ObjectDoesNotExist


class MDLCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    template_name = 'mdl-checkbox-select-multiple.html'

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        context['choices'] = [choice[1][0] for choice in context['widget']['optgroups']]
        context['name'] = name
        return self._render(self.template_name, context, renderer)


class LeafPackForm(forms.ModelForm):

    DEPLOYMENT_TYPE_CHOICES = (('Pool', 'Pool'), ('Riffle', 'Riffle'), ('Run', 'Run'))

    def __init__(self, *args, **kwargs):
        super(LeafPackForm, self).__init__(*args, **kwargs)
        if self.instance is not None and self.instance.pk is not None:
            other_types = self.instance.types.all().filter(created_by__isnull=False)
            self.initial['types_other'] = ', '.join([other.name for other in other_types])

    def save(self, commit=True):
        super(LeafPackForm, self).save(commit=commit)

        # LeafPackTypes from the cleaned form data. These types may or may not exist (i.e. they were created by a user)
        types_other_cleaned = self.cleaned_data.get('types_other', '').split(',')

        for other in types_other_cleaned:
            # remove leading/trailing white space
            other = other.strip()

            try:
                # if the type doesn't exist, skip over it since it's 'created_by' value will be empty
                lptype = LeafPackType.objects.get(name=other)
                self.instance.types.add(lptype)
            except ObjectDoesNotExist:
                continue

        self.instance.save()

    def clean(self):
        cleaned_data = super(LeafPackForm, self).clean()
        retrieval_count = cleaned_data.get('leafpack_retrieval_count', 0)
        placement_count = cleaned_data.get('leafpack_placement_count', 0)

        if retrieval_count > placement_count:
            self.add_error('leafpack_retrieval_count', forms.ValidationError(
                'The number of packs retrieved cannot exceed the number of packs placed!'))

        return self.cleaned_data

    site_registration = forms.ModelChoiceField(
        widget=forms.HiddenInput,
        queryset=SiteRegistration.objects.all()
    )

    types = forms.ModelMultipleChoiceField(
        widget=MDLCheckboxSelectMultiple,
        label='Enter the three predominant leaf species:',
        queryset=LeafPackType.objects.filter(created_by=None),
    )

    types_other = forms.CharField(
        max_length=255,
        label='Enter leaf species not listed above or experimental materials such as newspaper, plastic, etc.:',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'i.e., Species 1, Species 2, Species 3'})
    )

    placement_date = forms.DateField(
        label='Placement Date'
    )

    leafpack_placement_count = forms.IntegerField(
        label='Number of Packs Placed',
        min_value=1
    )

    placement_air_temp = forms.FloatField(
        label='Placement Air Temperature',
        required=False,
    )

    placement_water_temp = forms.FloatField(
        label='Placement Water Temperature',
        required=False,
    )

    retrieval_date = forms.DateField(
        label='Retrieval Date'
    )

    leafpack_retrieval_count = forms.IntegerField(
        label='Number of Packs Retrieved',
        min_value=1
    )

    retrieval_air_temp = forms.FloatField(
        label='Retrieval Air Temperature',
        required=False,
    )

    retrieval_water_temp = forms.FloatField(
        label='Retrieval Water Temperature',
        required=False,
    )

    had_storm = forms.NullBooleanField(
        label='Did storms occur while your leaf packs were in the stream?',
        required=False
    )

    storm_count = forms.IntegerField(
        label='Number of storms that occurred',
        min_value=0,
        required=False
    )

    storm_precipitation = forms.FloatField(
        label='Total precipitation that occurred',
        min_value=0,
        required=False
    )

    had_flood = forms.NullBooleanField(
        label='Did flooding occur?',
        required=False
    )

    had_drought = forms.NullBooleanField(
        label='Was this site experiencing a drought during your experiment?',
        required=False
    )

    deployment_type = forms.ChoiceField(
        choices=DEPLOYMENT_TYPE_CHOICES,
        label='Stream Habitat Type',
        required=False
    )

    notes = forms.CharField(
        label='Leave your comments',
        widget=forms.Textarea(),
        required=False
    )

    class Meta:
        model = LeafPack
        exclude = ['bugs']


class LeafPackBugForm(forms.ModelForm):
    class Meta:
        model = LeafPackBug
        fields = ['bug_count']

    bug_count = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance'].bug:
            kwargs['prefix'] = kwargs['instance'].bug.scientific_name

        super(LeafPackBugForm, self).__init__(*args, **kwargs)

        if self.instance and getattr(self.instance, 'bug', None):
            # Is the macroinvertebrate model instance a Family (in biological classification)?
            self.is_family = self.instance.bug.family_of is not None
            # Does the model instance have children?
            self.has_children = len(self.instance.bug.families.all()) > 0

            self.fields['bug_count'].label = self.instance.bug.display_name


class LeafPackBugFormFactory(forms.BaseFormSet):
    """
    NOTE: The terms 'Order' and 'Family' (or 'Families') in the comments refers to taxonomical biological
    classification.
    """

    def get_form_kwargs(self, index):
        kwargs = super(LeafPackBugFormFactory, self).get_form_kwargs(index)
        kwargs['instance'] = kwargs['bugs'][index]
        return kwargs

    @staticmethod
    def formset_factory(leafpack=None, taxon_forms=None):  # type: (LeafPack, [LeafPackBugForm]) -> list
        """
        Factory method to create a customized form set

        :param leafpack: An instance of LeafPack (optional).
        :param taxon_forms: An array of LeafPackBugForms(optional).

        :return []:

            Returns an array of tuples, where:

                Element 0 in each tuple is an instance of LeafPackBugForm:

                    - The 'Macroinvertebrate' object associated with LeafPackBugForm will be a parent taxon. These taxon
                      fall under the 'Order' category of taxonomic hierarchy.


                Element 1 in each tuple is a list of LeafPackBugForms:

                    - Each form's model instance is a taxon suborder of the parent taxon of the first element. These
                      taxon fall under the 'suborder' category of taxonomic hierarchy.

                    - this is an empty list if the parent taxon (in element 0) has no suborder taxons.


            Example:
                [
                    (LeafPackBugForm, []),
                    (LeafPackBugForm, [LeafPackBugForm]),
                    (LeafPackBugForm, [LeafPackBugForm, LeafPackBugForm])
                ]

        """
        form_list = []

        queryset = Macroinvertebrate.objects.filter(family_of=None).order_by('sort_priority')

        for taxon in queryset:
            if leafpack is not None:
                try:
                    lpg = LeafPackBug.objects.get(bug=taxon.id, leaf_pack=leafpack.id)
                except ObjectDoesNotExist:
                    lpg = LeafPackBug(bug=taxon, leaf_pack=leafpack)
                    lpg.save()
            else:
                lpg = LeafPackBug(bug=taxon)

            order_bug_form = LeafPackBugForm(instance=lpg)

            families = taxon.families.all().order_by('common_name').order_by('sort_priority')
            family_bug_forms = list()
            if len(families) > 0:

                if leafpack is not None:

                    child_taxons = []
                    for child_bug in families:

                        try:
                            child_lpg = LeafPackBug.objects.get(bug=child_bug, leaf_pack=leafpack)
                        except ObjectDoesNotExist:
                            child_lpg = LeafPackBug(bug=child_bug, leaf_pack=leafpack)
                            child_lpg.save()

                        child_taxons.append(child_lpg)

                    family_bug_forms = [LeafPackBugForm(instance=taxon) for taxon in child_taxons]
                else:
                    family_bug_forms = [LeafPackBugForm(instance=LeafPackBug(bug=bug)) for bug in families]

            form_list.append((order_bug_form, family_bug_forms))

        # If taxon_forms is not None, plug bug_count values into new formset
        if taxon_forms is not None:

            def get_taxon_count(taxon_):
                for tf in taxon_forms:
                    if tf.instance.bug == taxon_:
                        return tf.instance.bug_count
                return 0

            for forms_ in taxon_forms:
                forms_[0].initial['bug_count'] = get_taxon_count(forms_[0].instance.bug)

                for form in forms_[1]:
                    form.initial['bug_count'] = get_taxon_count(form.instance.bug)

        return form_list

    @staticmethod
    def grouped_formset_factory(leafpack=None, taxon_forms=None):
        """
        2019/10/11
        Factory method to create a customized form set

        :param leafpack: An instance of LeafPack (optional).
        :param taxon_forms: An array of LeafPackBugForms(optional).

        :return []:

        Example:
        [
            {'name':'group 1', 'list':[LeafPackBugForm, LeafPackBugForm, ...]},
            {'name':'group 2', 'list':[LeafPackBugForm, LeafPackBugForm, ...]},
            {'name':'group 3', 'list':[LeafPackBugForm, LeafPackBugForm, ...]}
        ]

        """
        groupedform_list = []
        groupRS= LeafPackSensitivityGroup.objects.all()

        for gr in groupRS:

            groupRS = Macroinvertebrate.objects.filter(displayflag= True, sens_group=gr)
            bug_forms=[]
            for taxon in groupRS:
                if leafpack is not None:
                    try:
                        lpg = LeafPackBug.objects.get(bug=taxon.id, leaf_pack=leafpack.id)
                    except ObjectDoesNotExist:
                        lpg = LeafPackBug(bug=taxon, leaf_pack=leafpack)
                        lpg.save()
                else:
                    lpg = LeafPackBug(bug=taxon)
                
                bug_form = LeafPackBugForm(instance=lpg)
                bug_forms.append(bug_form)
            
            group ={}
            group['name']= 'Group {0}: {1}'.format(str(gr.id), gr.name)
            group['list']= bug_forms
            groupedform_list.append(group)

        # If taxon_forms is not None, plug bug_count values into new formset
        if taxon_forms is not None:

            def get_taxon_count(taxon_):
                for tf in taxon_forms:
                    if tf.instance.bug == taxon_:
                        return tf.instance.bug_count
                return 0

            for forms_ in taxon_forms:
                forms_[0].initial['bug_count'] = get_taxon_count(forms_[0].instance.bug)

                for form in forms_[1]:
                    form.initial['bug_count'] = get_taxon_count(form.instance.bug)

        return groupedform_list

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.core.validators import RegexValidator, URLValidator
from django.http import Http404
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from rules.contrib.views import PermissionRequiredMixin

from dino.common.views import DeleteConfirmView
from dino.pdns_api import PDNSError, PDNSNotFoundException, pdns
from dino.synczones.models import Zone


class PDNSDataView():
    """ provide filtering and basic context for objects w/o a database """
    filter_properties = []
    max_objects = 20

    class SearchForm(forms.Form):
        q = forms.CharField(max_length=100, label="Search", required=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = PDNSDataView.SearchForm(initial={'q': self.request.GET.get('q')})
        objects = self.get_final_objects()
        context['objects'] = objects[:self.max_objects]
        context['count_all'] = len(objects)
        context['count_shown'] = len(context['objects'])
        return context

    def get_final_objects(self):
        q = self.request.GET.get('q')

        if q:
            return [
                o for o in self.get_objects()
                if any(
                    q in (o.get(p) if isinstance(o, dict) else getattr(o, p))
                    for p in self.filter_properties
                )
            ]
        else:
            return self.get_objects()


class ZoneListView(PDNSDataView, PermissionRequiredMixin, TemplateView):
    permission_required = 'tenants.list_zones'
    template_name = "zoneeditor/zone_list.html"
    filter_properties = ['name']

    def get_objects(self):
        # TODO: doing this every time the list is loaded is a bad idea
        Zone.import_from_powerdns(pdns().get_zones())
        zones = Zone.objects.all()
        if not self.request.user.is_superuser:
            zones = zones.filter(tenants__users=self.request.user)
        return zones


class ZoneNameValidator(RegexValidator):
    regex = fr'^{URLValidator.hostname_re}{URLValidator.domain_re}{URLValidator.tld_re}\Z'


class ZoneCreateForm(forms.Form):
    name = forms.CharField(validators=(ZoneNameValidator(),))

    def clean_name(self):
        name = self.cleaned_data['name']
        if not name.endswith('.'):
            name = name + '.'
        return name

    def _post_clean(self):
        if not self.errors:
            self.create_zone()

    def create_zone(self):
        try:
            pdns().create_zone(
                name=self.cleaned_data['name'],
                kind=settings.ZONE_DEFAULT_KIND,
                nameservers=settings.ZONE_DEFAULT_NAMESERVERS,
            )
        except PDNSError as e:
            self.add_error(None, f'PowerDNS error: {e.message}')


# TODO: add to tenant
class ZoneCreateView(PermissionRequiredMixin, FormView):
    permission_required = 'tenants.create_zone'
    template_name = "zoneeditor/zone_create.html"
    form_class = ZoneCreateForm

    def get_success_url(self):
        name = self.form.cleaned_data['name']
        return reverse('zoneeditor:zone_detail', kwargs={'zone': name})

    def form_valid(self, form):
        self.form = form  # give get_success_url access
        return super().form_valid(form)


class ZoneDetailMixin(PermissionRequiredMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zone_name'] = self.zone_name
        return context

    def get_permission_object(self):
        return self.zone_name

    @property
    def zone_name(self):
        return self.kwargs['zone']


class ZoneRecordsView(PDNSDataView, ZoneDetailMixin, TemplateView):
    permission_required = 'tenants.view_zone'
    template_name = "zoneeditor/zone_records.html"
    filter_properties = ['name']

    def get_objects(self):
        try:
            return pdns().get_records(self.zone_name)
        except PDNSNotFoundException:
            raise Http404()


# TODO: delete from DB
class ZoneDeleteView(PermissionRequiredMixin, DeleteConfirmView):
    permission_required = 'tenants.delete_zone'
    redirect_url = reverse_lazy('zoneeditor:zone_list')

    def delete_entity(self, pk):
        if not self.request.user.has_perm(self.permission_required, pk):
            raise PermissionDenied()

        pdns().delete_zone(pk)


class RecordCreateForm(forms.Form):
    name = forms.CharField()
    rtype = forms.ChoiceField(choices=settings.RECORD_TYPES, initial='A', label='Record Type')
    ttl = forms.IntegerField(min_value=1, initial=300, label='TTL')
    content = forms.CharField()

    def __init__(self, zone_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zone_name = zone_name

    def clean_name(self):
        name = self.cleaned_data['name']

        if not name.endswith('.'):
            name = name + '.'
        if not name.endswith('.' + self.zone_name):
            name = f'{name}{self.zone_name}'

        return name

    def _post_clean(self):
        if not self.errors:
            self.create_record()

    def create_record(self):
        try:
            pdns().create_record(
                zone=self.zone_name,
                name=self.cleaned_data['name'],
                rtype=self.cleaned_data['rtype'],
                ttl=self.cleaned_data['ttl'],
                content=self.cleaned_data['content'],
            )
        except PDNSError as e:
            self.add_error(None, f'PowerDNS error: {e.message}')


class RecordCreateView(ZoneDetailMixin, FormView):
    permission_required = 'tenants.create_record'
    template_name = "zoneeditor/record_create.html"
    form_class = RecordCreateForm

    def get_success_url(self):
        return reverse('zoneeditor:zone_detail', kwargs={'zone': self.zone_name})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['zone_name'] = self.zone_name
        return kwargs


class RecordDeleteView(ZoneDetailMixin, DeleteConfirmView):
    permission_required = 'tenants.delete_record'

    def get_display_identifier(self, rr):
        return f"{rr['rtype']} {rr['name']} {rr['content']}"

    def delete_entity(self, rr):
        # permission check is done based on kwarg, so make sure we use the same for deletion.
        # even without this check the delete would eventually fail because the client tries
        # to delete "www.example.com." out of zone "example.org.", which only makes sense
        # for every special constellations (e.g. "customer.com.internal.proxy").
        if rr['zone'] != self.kwargs['zone']:
            raise SuspiciousOperation('zone name in kwargs does not match zone name in payload.')
        pdns().delete_record(rr['zone'], rr['name'], rr['rtype'], rr['content'])

    def get_redirect_url(self, rr):
        return reverse('zoneeditor:zone_records', kwargs={'zone': rr['zone']})
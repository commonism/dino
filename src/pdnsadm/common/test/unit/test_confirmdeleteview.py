import pytest
from django import forms
from django.test import RequestFactory
from django.views.generic.base import TemplateView

from ...views import DeleteConfirmView


class T(DeleteConfirmView):
    redirect_url = '/success'

def test_deleteconfirmview_get():
    response = T.as_view()(RequestFactory().get('/'))
    assert response.status_code == 405

def test_deleteconfirmview_post_first(mocker, mock_delete_entity, mock_messages_success, signed_zone_name):
    c = T()
    c.request = RequestFactory().post('/', data={'identifier': signed_zone_name})
    response = c.post(c.request)
    mock_delete_entity.assert_not_called()
    mock_messages_success.assert_not_called()
    assert response.status_code == 200

def test_deleteconfirmview_post_canceled(mocker, mock_delete_entity, mock_messages_success, signed_zone_name):
    c = T()
    c.request = RequestFactory().post('/', data={'confirm': 'false', 'identifier': signed_zone_name})
    response = c.post(c.request)
    mock_delete_entity.assert_not_called()
    mock_messages_success.assert_not_called()
    assert response.status_code == 302
    assert response['Location'] == '/success'

def test_deleteconfirmview_post_confirmed(mocker, mock_delete_entity, mock_messages_success, signed_zone_name):
    c = T()
    c.request = RequestFactory().post('/', data={'confirm': 'true', 'identifier': signed_zone_name})
    response = c.post(c.request)
    mock_delete_entity.assert_called_once_with('example.com.')
    mock_messages_success.assert_called_once_with(c.request, 'example.com. has been deleted.')
    assert response.status_code == 302
    assert response['Location'] == '/success'

def test_deleteconfirmview_post_error(mocker, mock_messages_success, mock_messages_error, signed_zone_name):
    from pdnsadm.pdns_api import PDNSError
    delete_entity = mocker.patch('pdnsadm.common.views.DeleteConfirmView.delete_entity', side_effect=PDNSError('/', 400, 'something broke'))
    c = T()
    c.request = RequestFactory().post('/', data={'confirm': 'true', 'identifier': signed_zone_name})
    response = c.post(c.request)
    assert response.status_code != 302
    mock_messages_success.assert_not_called()
    assert 'PowerDNS error: something broke' in response.context_data['form'].errors['__all__']

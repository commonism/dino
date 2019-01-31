from collections import namedtuple

import pytest
from django.shortcuts import reverse
from django.test import TestCase


@pytest.mark.django_db()
def test_zonedeleteview_get(client_admin, mock_pdns_delete_zone):
    response = client_admin.get(reverse('zoneeditor:zone_delete'))
    assert response.status_code == 405
    mock_pdns_delete_zone.assert_not_called()

@pytest.mark.django_db()
def test_zonedeleteview_get_unauthenicated(client):
    url = reverse('zoneeditor:zone_delete')
    response = client.get(url)
    TestCase().assertRedirects(response, f'/accounts/login/?next={url}')

@pytest.mark.django_db()
def test_zonedeleteview_post(client_admin, mock_pdns_delete_zone, signed_example_com):
    response = client_admin.post(reverse('zoneeditor:zone_delete'), data={
        'identifier': signed_example_com,
        'confirm': 'true',
    })
    TestCase().assertRedirects(response, '/zones', fetch_redirect_response=False)
    mock_pdns_delete_zone.assert_called_once_with('example.com.')

@pytest.mark.django_db()
def test_zonedeleteview_post_unauthenicated(client):
    url = reverse('zoneeditor:zone_delete')
    response = client.post(url)
    TestCase().assertRedirects(response, f'/accounts/login/?next={url}')

@pytest.mark.django_db()
def test_zonedeleteview_post_no_confirm(client_admin, mock_pdns_delete_zone, signed_example_com):
    response = client_admin.post(reverse('zoneeditor:zone_delete'), data={
        'identifier': signed_example_com,
        'confirm': 'false',
    })
    TestCase().assertRedirects(response, '/zones', fetch_redirect_response=False)
    mock_pdns_delete_zone.assert_not_called()

@pytest.mark.django_db()
def test_zonedeleteview_post_empty_confirm(client_admin, mock_pdns_delete_zone, signed_example_com):
    response = client_admin.post(reverse('zoneeditor:zone_delete'), data={
        'identifier': signed_example_com,
    })
    assert 'example.com' in response.content.decode()
    mock_pdns_delete_zone.assert_not_called()

@pytest.mark.django_db()
def test_zonedeleteview_post_unknown_zone(client_admin, mocker, signed_example_com):
    from pdnsadm.pdns_api import PDNSError
    m = mocker.patch('pdnsadm.pdns_api.pdns.delete_zone', side_effect=PDNSError('/', 422, 'Could not find domain'))
    response = client_admin.post(reverse('zoneeditor:zone_delete'), data={
        'identifier': signed_example_com,
        'confirm': 'true',
    })
    content = response.content.decode()
    assert response.status_code != 302
    assert 'Could not find domain' in content

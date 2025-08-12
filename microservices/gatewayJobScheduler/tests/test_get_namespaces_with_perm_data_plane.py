import pytest
from app import get_namespaces_with_perm_data_plane

def test_get_namespaces_with_perm_data_plane_happy_path(mock_keycloak_clients):
    """Test successful retrieval of namespaces with matching perm-data-plane"""
    mock_kc = mock_keycloak_clients['admin_client']
    
    # Mock groups response
    mock_kc.get_groups.return_value = [
        {'id': 'group1', 'name': 'other-group'},
        {'id': 'ns-group-id', 'name': 'ns'}
    ]
    
    # Mock subgroups with various perm-data-plane values
    mock_kc.get_group.return_value = {
        'subGroups': [
            {
                'name': 'namespace1',
                'attributes': {
                    'perm-data-plane': ['test-dp', 'other-dp']
                }
            },
            {
                'name': 'namespace2',
                'attributes': {
                    'perm-data-plane': ['test-dp']
                }
            },
            {
                'name': 'namespace3',
                'attributes': {
                    'perm-data-plane': ['different-dp']
                }
            }
        ]
    }
    
    result = get_namespaces_with_perm_data_plane('test-dp')
    
    assert result == ['namespace1', 'namespace2']
    mock_kc.get_groups.assert_called_once()
    mock_kc.get_group.assert_called_once_with('ns-group-id')

def test_get_namespaces_with_perm_data_plane_no_ns_group(mock_keycloak_clients):
    """Test when 'ns' group doesn't exist"""
    mock_kc = mock_keycloak_clients['admin_client']
    
    # Mock groups response without 'ns' group
    mock_kc.get_groups.return_value = [
        {'id': 'group1', 'name': 'other-group'},
        {'id': 'group2', 'name': 'another-group'}
    ]
    
    result = get_namespaces_with_perm_data_plane('test-dp')
    
    assert result == []
    mock_kc.get_groups.assert_called_once()
    mock_kc.get_group.assert_not_called()

def test_get_namespaces_with_perm_data_plane_no_subgroups(mock_keycloak_clients):
    """Test when 'ns' group has no subgroups"""
    mock_kc = mock_keycloak_clients['admin_client']
    
    mock_kc.get_groups.return_value = [
        {'id': 'ns-group-id', 'name': 'ns'}
    ]
    
    # Mock empty subgroups
    mock_kc.get_group.return_value = {'subGroups': []}
    
    result = get_namespaces_with_perm_data_plane('test-dp')
    
    assert result == []
    mock_kc.get_group.assert_called_once_with('ns-group-id')

def test_get_namespaces_with_perm_data_plane_no_matching_namespaces(mock_keycloak_clients):
    """Test when no namespaces match the perm-data-plane value"""
    mock_kc = mock_keycloak_clients['admin_client']
    
    mock_kc.get_groups.return_value = [
        {'id': 'ns-group-id', 'name': 'ns'}
    ]
    
    mock_kc.get_group.return_value = {
        'subGroups': [
            {
                'name': 'namespace1',
                'attributes': {
                    'perm-data-plane': ['other-dp']
                }
            },
            {
                'name': 'namespace2',
                'attributes': {
                    'perm-data-plane': ['different-dp']
                }
            }
        ]
    }
    
    result = get_namespaces_with_perm_data_plane('test-dp')
    
    assert result == []

def test_get_namespaces_with_perm_data_plane_missing_attributes(mock_keycloak_clients):
    """Test namespaces with missing or empty attributes"""
    mock_kc = mock_keycloak_clients['admin_client']
    
    mock_kc.get_groups.return_value = [
        {'id': 'ns-group-id', 'name': 'ns'}
    ]
    
    mock_kc.get_group.return_value = {
        'subGroups': [
            {
                'name': 'namespace1',
                'attributes': {
                    'perm-data-plane': ['test-dp']
                }
            },
            {
                'name': 'namespace2',
                # Missing attributes
            },
            {
                'name': 'namespace3',
                'attributes': {
                    # Missing perm-data-plane
                    'other-attr': ['value']
                }
            },
            {
                'name': 'namespace4',
                'attributes': {
                    'perm-data-plane': []  # Empty list
                }
            }
        ]
    }
    
    result = get_namespaces_with_perm_data_plane('test-dp')
    
    assert result == ['namespace1']

def test_get_namespaces_with_perm_data_plane_missing_subgroups_key(mock_keycloak_clients):
    """Test when get_group response doesn't have subGroups key"""
    mock_kc = mock_keycloak_clients['admin_client']
    
    mock_kc.get_groups.return_value = [
        {'id': 'ns-group-id', 'name': 'ns'}
    ]
    
    # Mock response without subGroups key
    mock_kc.get_group.return_value = {}
    
    result = get_namespaces_with_perm_data_plane('test-dp')
    
    assert result == []
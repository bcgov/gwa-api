from flask import current_app as app

def get_data_plane(ns_attributes):
    default_data_plane = app.config['defaultDataPlane']
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]

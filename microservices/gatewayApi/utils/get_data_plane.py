from flask import current_app as app


class DataPlaneNotConfiguredError(Exception):
    def __init__(self, data_plane):
        super().__init__("Data plane '%s' is not configured" % data_plane)
        self.data_plane = data_plane


def get_data_plane(ns_attributes):
    default_data_plane = app.config['defaultDataPlane']
    return ns_attributes.get('perm-data-plane', [default_data_plane])[0]


def get_data_plane_config(data_plane):
    data_planes = app.config['data_planes']
    if data_plane not in data_planes:
        raise DataPlaneNotConfiguredError(data_plane)
    return data_planes[data_plane]

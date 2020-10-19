
# Catalog:
# This API allows an authorized user to update the BC Data Catalog
# record for their apis that are managed under the particular namespace.
#
# It will make calls to BCDC using an admin account to manage the
# dataset record for each API.
#


import os
import logging
import requests
import json
from flask import Blueprint, jsonify, request, Response, make_response, abort, g, current_app as app

from clients.bcdc import Client

from v1.auth.auth import admin_jwt, enforce_authorization

cat = Blueprint('catalog', 'catalog')

@cat.route('/<string:package_id>',
           methods=['DELETE'], strict_slashes=False)
#@admin_jwt(None)
def delete_package(namespace: str, package_id: str) -> object:
    bcdc_client = Client()
    settings = app.config['bcdc']

    try:
        package = bcdc_client.package_delete(package=package_id, api_key=settings['BCDC_API_KEY'])
        app.logger.debug("Deleted metadata record: {}".format(package))
    except (ValueError, RuntimeError) as e: 
        raise e

    return make_response("", 204)



@cat.route('/',
           methods=['POST'], strict_slashes=False)
#@admin_jwt(None)
def create_package(namespace: str) -> object:
    bcdc_client = Client()

    #headers
    contentType = request.headers.get('Content-Type')

    #check content type of request req_data
    if not contentType or contentType != "application/json":
        return jsonify({"msg": "Invalid Content-Type.  Expecting application/json"}), 400

    #get request req_data
    try:
        req_data = request.get_json()
    except RuntimeError as e:
        return jsonify({"msg": "content req_data is not valid json"}), 400

    try:
        req_data = clean_and_validate_req_data(req_data)
    except ValueError as e:
        return jsonify({"msg": "{}".format(e)}), 400
    except RuntimeError as e:
        app.logger.error("{}".format(e));
        return jsonify({"msg": "An unexpected error occurred while validating the API registration request."}), 500

    success_resp = {}
    metadata_web_url = None

    #create a draft metadata record (if one doesn't exist yet)
    if not req_data.get("existing_metadata_url"):
        package = None
        try:
            package = create_package(req_data)
            if not package:
                raise ValueError("Unknown reason")
            #add info about the new metadata record to the response
            metadata_web_url = bcdc_client.package_id_to_web_url(package["id"])
            metadata_api_url = bcdc_client.package_id_to_api_url(package["id"])
            success_resp["new_metadata_record"] = {
                "id": package["id"],
                "web_url": metadata_web_url,
                "api_url": metadata_api_url
            }
        except ValueError as e: #user input errors cause HTTP 400
            return jsonify({"msg": "Unable to create metadata record in the BC Data Catalog. {}".format(e)}), 400
        except RuntimeError as e: #unexpected system errors cause HTTP 500
            app.logger.error("Unable to create metadata record in the BC Data Catalog. {}".format(e))
            return jsonify({"msg": "Unable to create metadata record in the BC Data Catalog."}), 500

        try:
            create_api_root_resource(package["id"], req_data)
        except ValueError as e: #perhaps other errors are possible too??  if so, catch those too
            app.logger.error(e)
            app.logger.warn("Unable to create API root resource associated with the new metadata record. {}".format(e))
    
        try:
            create_api_spec_resource(package["id"], req_data)
        except ValueError as e: #perhaps other errors are possible too??  if so, catch those too
            app.logger.error(e)
            app.logger.warn("Unable to create API spec resource associated with the new metadata record. {}".format(e))

        if 'metadata_details' in req_data and 'resources' in req_data['metadata_details']:
            for res in req_data['metadata_details']['resources']:
                resource = {
                    "package_id": package["id"], 
                    "url": res['url'],
                    "format": res['format'],
                    "name": res['name']
                }
                print(json.dumps(create_resource(resource), indent=4))
                
        return make_response(jsonify(message="Package created successfully", results=success_resp))

    #there is an existing metadata record
    else:
        metadata_web_url = req_data.get("existing_metadata_url")

        return make_response(jsonify([]))

def clean_and_validate_req_data(req_data):
  bcdc_client = Client()

  #ensure req_data folder hierarchy exists
  #---------------------------------------
  if not req_data:
    req_data = {}
  if not req_data.get("submitted_by_person"):
    req_data["submitted_by_person"] = {}
  if not req_data.get("metadata_details"):
    req_data["metadata_details"] = {}
  if not req_data["metadata_details"].get("owner"):
    req_data["metadata_details"]["owner"] = {}
  if not req_data["metadata_details"]["owner"].get("contact_person"):
    req_data["metadata_details"]["owner"]["contact_person"] = {}
  if not req_data["metadata_details"].get("security"):
    req_data["metadata_details"]["security"] = {}
  if not req_data["metadata_details"].get("license"):
    req_data["metadata_details"]["license"] = {}
  if not req_data.get("existing_api"):
    req_data["existing_api"] = {}
  if not req_data.get("gateway"):
    req_data["gateway"] = {}

  #check that required fields are present
  #--------------------------------------
  if not req_data["metadata_details"].get("title"):
    raise ValueError("Missing '$.metadata_details.title'")
  if not req_data["metadata_details"].get("description"):
    raise ValueError("Missing '$.metadata_details.description'")

  if not req_data["metadata_details"]["owner"].get("org_id"):
    raise ValueError("Missing '$.metadata_details.owner.org_id'")
  
  if not req_data["metadata_details"]["owner"]["contact_person"].get("name"):
    raise ValueError("Missing '$.metadata_details.owner.contact_person.name'")
  if not req_data["metadata_details"]["owner"]["contact_person"].get("business_email"):
    raise ValueError("Missing '$.metadata_details.owner.contact_person.business_email'") 

  if not req_data["metadata_details"]["security"].get("download_audience"):
    raise ValueError("Missing '$.metadata_details.security.download_audience'")
  if not req_data["metadata_details"]["security"].get("view_audience"):
    raise ValueError("Missing '$.metadata_details.security.view_audience'")
  if not req_data["metadata_details"]["security"].get("metadata_visibility"):
    raise ValueError("Missing '$.metadata_details.security.metadata_visibility'")
  if not req_data["metadata_details"]["security"].get("security_class"):
    raise ValueError("Missing '$.metadata_details.security.security_class'")

  if not req_data["metadata_details"]["license"].get("license_id"):
    raise ValueError("Missing '$.metadata_details.license.license_id'")

  if not req_data["submitted_by_person"].get("name"):
    raise ValueError("Missing '$.submitted_by_person.name'")
  if not req_data["submitted_by_person"].get("org_id") and not req_data["submitted_by_person"].get("org_name"):
    raise ValueError("Missing one of '$.submitted_by_person.org_id' or '$submitted_by_person.org_name'")
  if not req_data["submitted_by_person"].get("business_email"):
    raise ValueError("Missing '$.submitted_by_person.business_email'")

  if not req_data["existing_api"].get("base_url"):
    raise ValueError("Missing '$.existing_api.base_url'")

#  if not req_data["gateway"].get("use_gateway"):
#    raise ValueError("Missing '$.gateway.use_gateway'")

  #clean fields
  #------------
  #change Title to title-case.  This can be problematic for abbreviations, such as "BC" (which becomes "Bc")
  #req_data["metadata_details"]["title"] = req_data["metadata_details"]["title"].title()

  #defaults
  #--------
  if not req_data["metadata_details"]["owner"]["contact_person"].get("org_id"):
    req_data["metadata_details"]["owner"]["contact_person"]["org_id"] = req_data["metadata_details"]["owner"].get("org_id")
  if not req_data["metadata_details"]["owner"]["contact_person"].get("sub_org_id"):
    req_data["metadata_details"]["owner"]["contact_person"]["sub_org_id"] = req_data["metadata_details"]["owner"].get("sub_org_id")

  #validate field values
  #---------------------
  req_data["validated"] = {}
  owner_org = bcdc_client.get_organization(req_data["metadata_details"]["owner"].get("org_id"))
  if owner_org:
    req_data["validated"]["owner_org_name"] = owner_org["title"]
  else:
    raise ValueError("Unknown organization specified in '$.metadata_details.owner.org_id'")    
  
  owner_sub_org = bcdc_client.get_organization(req_data["metadata_details"]["owner"].get("sub_org_id"))
  if owner_sub_org:
    req_data["validated"]["owner_sub_org_name"] = owner_sub_org["title"]    
  
  owner_contact_org = bcdc_client.get_organization(req_data["metadata_details"]["owner"]["contact_person"].get("org_id"))
  if owner_contact_org:
    req_data["validated"]["owner_contact_org_name"] = owner_contact_org["title"]
  else:
    raise ValueError("Unknown organization specified in '$.metadata_details.owner.contact_person.org_id'")

  owner_contact_sub_org = bcdc_client.get_organization(req_data["metadata_details"]["owner"]["contact_person"].get("sub_org_id"))
  if owner_contact_sub_org:
    req_data["validated"]["owner_contact_sub_org_name"] = owner_contact_sub_org["title"]

  submitted_by_person_org = bcdc_client.get_organization(req_data["submitted_by_person"].get("org_id"))
  if submitted_by_person_org:
    req_data["validated"]["submitted_by_person_org_name"] = submitted_by_person_org["title"]

  submitted_by_person_sub_org = bcdc_client.get_organization(req_data["submitted_by_person"].get("sub_org_id"))
  if submitted_by_person_sub_org:
    req_data["validated"]["submitted_by_person_sub_org_name"] = submitted_by_person_sub_org["title"]

  if not submitted_by_person_org:
    req_data["validated"]["submitted_by_person_org_name"] = req_data["submitted_by_person"].get("org_name")


  return req_data

def create_package(req_data):
  """
  Registers a new package with BCDC
  :param req_data: the req_data of the http request to the /register resource
  """
  bcdc_client = Client()
  settings = app.config['bcdc']

  if 'metadata_details' in req_data and 'tags' in req_data['metadata_details']:
    tags = []
    for tag in req_data['metadata_details']['tags']:
        tags.append({"name": tag['name']})
  else:
    tags = [{"name": "API"}]

  package_dict = {
    "title": req_data["metadata_details"].get("title"),
    "name": bcdc_client.prepare_package_name(req_data["metadata_details"].get("title")),
    "org": settings['BCDC_PACKAGE_OWNER_ORG_ID'],
    "sub_org": settings['BCDC_PACKAGE_OWNER_SUB_ORG_ID'],
    "owner_org": settings['BCDC_PACKAGE_OWNER_SUB_ORG_ID'],
    "notes": req_data["metadata_details"].get("description"),
    "groups": [{"id" : settings['BCDC_GROUP_ID']}],
    "state": "active",
    "resource_status": req_data["metadata_details"].get("status", "completed"),
    "type": "WebService",
    "tag_string": "API",
    "tags": tags,
    "sector": "Service",
    "edc_state": "DRAFT",
    "download_audience": req_data["metadata_details"]["security"].get("download_audience"),
    "view_audience":  req_data["metadata_details"]["security"].get("view_audience"),
    "metadata_visibility": req_data["metadata_details"]["security"].get("metadata_visibility"),
    "security_class": req_data["metadata_details"]["security"].get("security_class"),
    "license_id": req_data["metadata_details"]["license"].get("license_id"),
#    "license_title": req_data["metadata_details"]["license"].get("license_title"), #auto added if license_id is specified
#    "license_url": "http://www2.gov.bc.ca/gov/content/home/copyright", #auto added if license_id is specified
    "contacts": [
      {
        "name": req_data["metadata_details"]["owner"]["contact_person"].get("name"),
        "organization": req_data["metadata_details"]["owner"]["contact_person"].get("org_id", settings['BCDC_PACKAGE_OWNER_ORG_ID']),
        "branch": req_data["metadata_details"]["owner"]["contact_person"].get("sub_org_id", settings['BCDC_PACKAGE_OWNER_SUB_ORG_ID']),
        "email": req_data["metadata_details"]["owner"]["contact_person"].get("business_email"),
        "role": req_data["metadata_details"]["owner"]["contact_person"].get("role", "pointOfContact"),
        "private": req_data["metadata_details"]["owner"]["contact_person"].get("private", "Display")
      }
    ]
  }
  print(json.dumps(package_dict, indent=4))
  try:
    package = bcdc_client.package_create(package_dict, api_key=settings['BCDC_API_KEY'])
    app.logger.debug("Created metadata record: {}".format(bcdc_client.package_id_to_web_url(package["id"])))
    return package
  except (ValueError, RuntimeError) as e: 
    raise e

def create_api_root_resource(package_id, req_data):
  """
  Adds a new resource to the given package.  The new resource represents the base URL of the API.
  :param package_id: the id of the package to add the resource to.
  :param req_data: the req_data of the request to /register as a dictionary
  :return: the new resource
  """
  bcdc_client = Client()
  settings = app.config['bcdc']

  #download api base url and check its content type (so we can create a 'resource' 
  #with the appropriate content type)
  format = "text"
  try:
    r = requests.get(req_data["existing_api"]["base_url"])
    if r.status_code < 400:
      resource_content_type = r.headers['content-type']
      format = content_type_to_format(resource_content_type, "text")
  except requests.exceptions.ConnectionError as e:
    app.logger.warning("Unable to access API '{}' to determine content type.".format(req_data["existing_api"]["base_url"]))
    pass

  #add the "API root" resource to the package
  resource_dict = {
    "package_id": package_id, 
    "url": req_data["existing_api"]["base_url"],
    "format": format, 
    "name": "API root"
  }
  resource = bcdc_client.resource_create(resource_dict, api_key=settings['BCDC_API_KEY'])
  return resource

def create_api_spec_resource(package_id, req_data):
  """
  Adds a new resource to the given package.  The new resource represents the API spec.
  This function fails does nothing and returns None if $.existing_api.openapi_spec_url is not
  present in req_data.
  :param package_id: the id of the package to add the resource to.
  :param req_data: the body of the request to /register as a dictionary
  :return: the new resource
  """
  bcdc_client = Client()
  settings = app.config['bcdc']

  if req_data["existing_api"].get("openapi_spec_url"):
    resource_dict = {
      "package_id": package_id, 
      "url": req_data["existing_api"]["openapi_spec_url"],
      "format": "openapi-json",
      "name": "API specification"
    }
    resource = bcdc_client.resource_create(resource_dict, api_key=settings['BCDC_API_KEY'])
    return resource

  return None

def create_resource(resource_dict):
    """
    Adds a new resource to the given package.
    """
    bcdc_client = Client()
    settings = app.config['bcdc']

    resource = bcdc_client.resource_create(resource_dict, api_key=settings['BCDC_API_KEY'])
    return resource

def content_type_to_format(content_type, default=None):
  """
  Converts a content type (aka mine type, as would appear in the Content-Type header 
  of an HTTP request or response) into corresponding ckan resource string (html, json, xml, etc.)
  """
  if content_type.startswith("text/html"):
    return "html"
  if content_type.startswith("application/json"):
    return "json"
  if "xml" in content_type:
    return "xml"
  return default
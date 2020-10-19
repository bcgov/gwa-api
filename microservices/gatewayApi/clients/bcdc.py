import json
import requests
import re
from flask import current_app as app

class Client():
    def __init__(self):
        self.settings = app.config['bcdc']

    def get_organization(self, org_id):
        """
        Gets an organization given its id
        :param org_id: the id of the organiztion to fetch
        """
        if not org_id:
            return None

        url = "{}{}/action/organization_show?id={}".format(self.settings['BCDC_BASE_URL'], self.settings['BCDC_API_PATH'], org_id)
        
        headers = {
            "Content-Type": "application/json",
        }
        r = requests.get(url, 
            headers=headers
            )
        
        if r.status_code == 404:
            return None
        elif r.status_code >= 400:
            raise RuntimeError("Unable to fetch organization by id from BCDC. URL was: {}".format(url))
            #raise ValueError("HTTP {} - {}".format(r.status_code, r.text))
        
        #get the response object
        response_dict = json.loads(r.text)
        assert response_dict['success'] is True
        organization = response_dict['result']

        return organization

    def package_create(self, package_dict, api_key=None):
            """
            Creates a new package (dataset) in BCDC
            :param package_dict: a dictionary with all require package properties
            :param user: the username to create the package under
            :param password: the password associated with the user
            """
            url = "{}{}/action/package_create".format(self.settings['BCDC_BASE_URL'], self.settings['BCDC_API_PATH'])
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": api_key
            }
            r = requests.post(url, 
                data=json.dumps(package_dict),
                headers=headers
                )
            
            #A list of http codes returned by BCDC's package_create resource which correspond to errors
            #in the input data
            USER_INPUT_ERROR_CODES = [400, 409]

            if r.status_code >= 400 and r.status_code not in USER_INPUT_ERROR_CODES:
                raise RuntimeError("Unable to create metadata record")

            #get the response object
            response_dict = json.loads(r.text)
            
            if r.status_code in USER_INPUT_ERROR_CODES:
                error_msg = response_dict.get("error", {}).get("name")
                if isinstance(error_msg, list):
                    error_msg = " ".join(error_msg)
                raise ValueError("{}".format(error_msg))
            #  r.raise_for_status()
            #  print(r.text)
            
            created_package = response_dict['result']
            return created_package


    def package_delete(self, package, api_key):
        """
        deletes a package
        """
        url = "{}{}/action/package_delete?id=".format(self.settings['BCDC_BASE_URL'], self.settings['BCDC_API_PATH'])
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": api_key
        }
        data={
            "id": package
        }
        r = requests.post(url, 
            data=json.dumps(data),
            headers=headers
        )
        
        if r.status_code >= 400:
            raise ValueError("{} {}".format(r.status_code, r.text))
        print(r.status_code)
        print(r.text)

    def resource_create(self, resource_dict, api_key=None):
        """
        Creates a new resource associated with a given package
        :param package_id: the id of the package to associate the resource with
        :param url: the url of the resource
        """
        url = "{}{}/action/resource_create".format(self.settings['BCDC_BASE_URL'], self.settings['BCDC_API_PATH'])
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": api_key
        }
        r = requests.post(url, 
            data=json.dumps(resource_dict),
            headers=headers
            )

        if r.status_code >= 400:
            raise ValueError("{} {}".format(r.status_code, r.text))
        #  r.raise_for_status()
        #  print(r.text)
        
        #get the response object
        response_dict = json.loads(r.text)
        assert response_dict['success'] is True
        created_package = response_dict['result']

        return created_package

    def package_id_to_web_url(self, package_id):
        """
        the web url needed to access a given package
        """
        return "{}/dataset/{}".format(self.settings['BCDC_BASE_URL'], package_id)

    def package_id_to_api_url(self, package_id):
        """
        the web url needed to access a given package
        """
        return "{}{}/action/package_show?id={}".format(self.settings['BCDC_BASE_URL'], self.settings['BCDC_API_PATH'], package_id)

    def prepare_package_name(self, s):
        s = s.lower()
        s = re.sub('[\W\s]+', '-', s)
        return s
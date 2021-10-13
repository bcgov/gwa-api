from fastapi import Request, HTTPException
from fastapi.logger import logger
from fastapi.param_functions import Depends
from fastapi.security import OAuth2PasswordBearer
from authlib.jose import jwt
from authlib.jose.errors import DecodeError, InvalidClaimError
from config import settings
import requests

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')


def retrieve_token(authorization, issuer, scope='openid'):
    headers = {
        'accept': 'application/json',
        'authorization': authorization,
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'scope': scope,
    }
    url = issuer + '/token'
    response = requests.post(url, headers=headers, data=data)

    if response.status_code == requests.codes.OK:
        return response.json()
    else:
        raise HTTPException(status_code=400, detail=response.text)


def validate_token(token: str = Depends(oauth2_scheme, use_cache=False)):
    try:
        token_str = token
        server_url = settings.resourceAuthServer['serverUrl']
        realm = settings.resourceAuthServer['realm']
        baseUrl = "%srealms/%s" % (server_url, realm)

        aud = settings.tokenMatch["aud"]

        server_metadata = OIDCDiscovery(baseUrl)

        # Fetch the public key for validating Bearer token
        jwk_r = requests.get(server_metadata['jwks_uri'])
        if jwk_r.status_code != 200:
            raise HTTPException(status_code=jwk_r.status_code,
                                detail="Error getting jwk from url: %s" % {server_metadata['jwks_uri']})
        jwk = jwk_r.json()
        token = jwt.decode(token, jwk)
        token.validate()
        if token.get("aud") is not None and aud not in token.get("aud"):
            raise InvalidClaimError("aud")
    except DecodeError as err:
        raise HTTPException(status_code=400, detail="Invalid token: %s" % str(err))
    except InvalidClaimError as ex:
        raise HTTPException(status_code=403, detail=str(ex))
    except Exception as ex:
        raise HTTPException(status_code=401, detail=str(ex))
    return token_str


def validate_admin_token(token: str = Depends(oauth2_scheme, use_cache=False)):
    try:
        token_str = token
        server_url = settings.resourceAuthServer['serverUrl']
        realm = settings.resourceAuthServer['realm']
        baseUrl = "%srealms/%s" % (server_url, realm)

        aud = settings.tokenMatch["admin-aud"]

        server_metadata = OIDCDiscovery(baseUrl)

        # Fetch the public key for validating Bearer token
        jwk_r = requests.get(server_metadata['jwks_uri'])
        if jwk_r.status_code != 200:
            raise HTTPException(status_code=jwk_r.status_code,
                                detail="Error getting jwk from url: %s" % {server_metadata['jwks_uri']})
        jwk = jwk_r.json()
        token = jwt.decode(token, jwk)

        token.validate()
        if token.get("aud") is not None and aud not in token.get("aud"):
            print(aud)
            raise InvalidClaimError("aud")
    except DecodeError as err:
        raise HTTPException(status_code=400, detail="Invalid token: %s" % str(err))
    except InvalidClaimError as ex:
        raise HTTPException(status_code=403, detail=str(ex))
    except Exception as ex:
        raise HTTPException(status_code=401, detail=str(ex))
    return token_str


def OIDCDiscovery(base_url):
    # Fetch the openid metadata so we may know the jwk endpoint uri
    server_metadata_url = f"{base_url}/.well-known/openid-configuration"
    server_metadata_r = requests.get(server_metadata_url)
    if server_metadata_r.status_code != 200:
        raise HTTPException(status_code=server_metadata_r.status_code,
                            detail="Error getting auth server metadata from url: %s" % {server_metadata_url})
    server_metadata = server_metadata_r.json()
    return server_metadata


def validate_permissions(rqst: Request, token: str = Depends(validate_token, use_cache=False)):
    pat = get_token()
    rsid = map_res_name_to_id(pat['access_token'], rqst.path_params['namespace'])
    if check_permissions(token, [("permission", "%s#%s" % (rsid, "GatewayConfig.Publish"))]) == False:
        raise HTTPException(
            status_code=403, detail="Not authorized to access namespace %s with GatewayConfig.Publish" % rqst.path_params['namespace'])


def get_token():
    conf = settings.resourceAuthServer

    tokenUrl = "%srealms/%s/protocol/openid-connect/token" % (conf['serverUrl'], conf['realm'])

    data = {
        "grant_type": "client_credentials",
        "client_id": conf['clientId'],
        "client_secret": conf['clientSecret']
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    print(tokenUrl)
    r = requests.post(tokenUrl, headers=headers, data=data)

    logger.debug("[get_token] %s" % r.status_code)
    json = r.json()
    return json


def check_permissions(access_token, permissions):
    conf = settings.resourceAuthServer

    tokenUrl = "%srealms/%s/protocol/openid-connect/token" % (conf['serverUrl'], conf['realm'])

    headers = {
        "Authorization": "Bearer %s" % access_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = [
        ("grant_type", "urn:ietf:params:oauth:grant-type:uma-ticket"),
        ("audience", conf['clientId']),
        ("submit_request", False),
        ("response_mode", "decision"),
    ] + permissions

    logger.debug("[check_permissions] %s" % permissions)
    logger.debug("[check_permissions] %s" % tokenUrl)
    r = requests.post(tokenUrl, headers=headers, data=data)
    logger.debug("[check_permissions] %s" % r.status_code)
    json = r.json()
    logger.debug("[check_permissions] %s" % json)
    return ('error' in json or json['result'] == False) == False


def map_res_name_to_id(pat_token, name):
    conf = settings.resourceAuthServer

    tokenUrl = "%srealms/%s/authz/protection/resource_set?name=%s&exactName=true" % (
        conf['serverUrl'], conf['realm'], name)

    headers = {
        "Authorization": "Bearer %s" % pat_token,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    logger.debug("[map_res_name_to_id] %s" % name)

    r = requests.get(tokenUrl, headers=headers)
    logger.debug("[map_res_name_to_id] %s" % r.status_code)
    json = r.json()
    logger.debug("[map_res_name_to_id] %s" % json)
    if len(json) == 0:
        return None
    else:
        return json[0]

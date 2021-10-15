from fastapi import Request, HTTPException


def users_group_root():
    return 'ns'


def admins_group_root():
    return 'ns-admins'


def ns_claim():
    return 'namespace'


def enforce_authorization(rqst: Request, namespace):
    the_ns_claim = ns_claim()

    if the_ns_claim not in rqst.state.token_principal:
        raise HTTPException(status_code=403, detail="Missing Claims.")

    # Make sure namespace matches the one in the claim
    # It can be in two formats: '/ns/<namespace>' or '<namespace>'
    ns = rqst.state.token_principal[the_ns_claim]
    if ns != namespace and ns != ('/%s/%s' % (users_group_root(), namespace)):
        raise HTTPException(status_code=403, detail="Not authorized to use %s namespace." % namespace)

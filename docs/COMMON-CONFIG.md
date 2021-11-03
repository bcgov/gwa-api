# Common Gateway Controls

The following are sample Gateway controls for common scenarios.

## Returning an HTTP Redirect

```
plugins:
- name: pre-function
    tags: [ _NS_ ]
    config:
      access:
      - "kong.response.exit(307, 'site moved - redirecting...', {['Location'] = 'https://my-new-url.site'})"
```

## Adding Headers For Best Security Practices

```
plugins:
- name: response-transformer
  tags: [ _NS_ ]
  config:
    add:
      headers:
      - "X-Frame-Options: DENY"
      - "X-XSS-Protection: 1; mode=block"
      - "X-Content-Type-Options: nosniff"
      - "Strict-Transport-Security: max-age=31536000"
      - "Content-Security-Policy: script-src 'self'"
```

> For further information on individual headers, see: https://owasp.org/www-project-secure-headers/

## Rate Limit

### Option 1 - Using a Distributed Cache

This provides the most accurate because it uses a centralized Cache that all Kong nodes use.  The downside is that there is a 100-200ms latency.

```
plugins:
- name: rate-limiting
  tags: [ _NS_ ]
  config:
    fault_tolerant: true
    hide_client_headers: false
    limit_by: ip
    minute: 30000
    second: null
    hour: null
    day: null
    month: null
    year: null
```

### Option 2 - Node Local Caching

This provides the fastest rate limiting option, with minimal latency (~1ms).  The downside is that it is local to each node so calculating the actual load on your upstream is a function of the number of nodes.

```
plugins:
- name: rate-limiting
  tags: [ _NS_ ]
  config:
    policy: local
    fault_tolerant: true
    hide_client_headers: false
    limit_by: ip
    minute: 30000
    second: null
    hour: null
    day: null
    month: null
    year: null
```

## Two-tiered access setup

The `key-auth` and `jwt-keycloak` plugins support the concept of allowing "anonymous" access, which allows you to define a "free" service which might have limits around it (like only allowing 100 requests/minute), and then an "elevated" access where the Consumer would get an improved level of service, such as higher rate limits.

There is a global "anonymous" consumer that is identified as "ce26955a-cf08-4907-9427-12d01c8bd94c" in both our Test and Production environments.

To enable anonymous access to your API, update your plugin configuration with:

### key-auth

```
- name: key-auth
  tags: [ _NS_ ]
  config:
    ...
    anonymous: ce26955a-cf08-4907-9427-12d01c8bd94c      
```

### jwt-keycloak

```
- name: jwt-keycloak
  tags: [ _NS_ ]
  config:
    ...
    consumer_match: true
    consumer_match_ignore_not_found: false
    consumer_match_claim_custom_id: false
    anonymous: ce26955a-cf08-4907-9427-12d01c8bd94c      
```

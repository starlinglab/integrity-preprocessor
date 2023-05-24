`BROWSERTRIX_CREDENTIALS`

This file contains all the credentials for all the browsertrix instance that the preprocessor will use.
Example `browsertrix_credentials.json`
```
{
    "browsertrix.example.org": {
        "login": "example@example.org",
        "password": "password"
    }
}
```

`CONFIG_FILE` 

Example `preprocessor-browsertrix.json`

This file maps the organization ID in browsertrix to the integrity collection/organizaiton. It also additional metadata.

```
{
  "collections": {
    "GUID-OF-ORGANIZATION-IN-BROWSERTRIX": {
      "collectionID": "example-collection",
      "organizationID": "demo-org",
      "target_path": "/mnt/integrity_store/starling/internal/demo-org/example-collection/",
      "author": {
        "@type": "Organization",
        "identifier": "https://cat.example ",
        "name": "Example user"
      }
      "server": "browsertrix.example.org"
    }
}
```

`provisionBrowsertrixAccounts.py`

This tool automatically creates organizations in Browsertrix and generates a resulting `CONFIG_FILE` file.  

example `preprocessor-browsertrix-collections.json`
```
[
  {
    "collectionID": "catz-online",
    "server": "org1.browsertrix.dev.starlinglab.org",
    "orgID": "demo-org",
    "author": {
      "@type": "Organization",
      "identifier": "https://cat.example ",
      "name": "I C Cats"
    }
  }
]
```

# Browsertrix

## .env
| Env Var                 | Description                                                  | Required |
| ----------------------- | ------------------------------------------------------------ | -------- |
| BROWSERTRIX_CREDENTIALS | Path to a json that holds the browsertrix credentials        | YES      |
| TMP_DIR                 | Path to store temporary files                                | YES      |
| DATA_FILE               | Path to file that keeps track of what crawl                  | YES      |
| PROMETHEUS_FILE         | Path to node exporter data will be saved                     | YES      |
| CONFIG_FILE             | Path to configuration                                        | YES      |
| HOSTNAME                | Define url that will be used to download the WACZ            | YES      |
| TARGET_PATH             | Path to the default directory where bundles are to be placed | Yes      |

# BROWSERTRIX_CREDENTIALS

JSON file that holds a dict of hostname. Each hostname has a LOGIN and PASSWORD to that Browsertrix server


```JSON
{
    "BROWSERTRIX.SERVER.HOST.NAME.COM": {
        "login": "someuser@example.com",
        "password": "supersecretpassword"
    }
}
```

# CONFIG_FILE

JSON contains a key called collections. In this is a dict of Organization ID (OID) for each organization created in Browsertrix. Each organization has the following keys

| Key             | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| collectionID    | collection id as identified by the backend                  |
| organizationID  | organization id as identified by the backend                |
| target_path     | Path to the root of organization/collection on the backend  |
| author          | Standard author key structure to add to metadata            |
| server          | Hostname of server as identified by BROWSERTRIX_CREDENTIALS |

```json
{
  "collections": {
    "AIDAID-AIDAID-AIDAID-AIDAID-AIDAIDAIDAID": {
      "collectionID": "name-of-collection",
      "organizationID": "name-of-org",
      "target_path": "/mnt/integrity_store/starling/internal/name-of-collection/name-of-org/",
      "author": {
        "@type": "Organization",
        "identifier": "Some Org",
        "name": "https://example.com"
      },
      "server": "BROWSERTRIX.SERVER.HOST.NAME.COM"
    }    
  }
}
```

# DATA_FILE

This file will be created on first run.
# provision-collections.py

This tool will provision collections in a browsertrix install generating required organizations and GUIDs.  

It reads a JSON structure from `{config_path}preprocessor-browsertrix-collections.json` and generate the collections config file in `CONFIG_FILE` that includes the GUID of these collections.

It reads the enviroment file at `/root/integrity-preprocessor/browsertrix/.env` and the credentials defined in the `BROWSERTRIX_CREDENTIALS` file. The 

```
config_path = "/root/.integrity/"
base_url = "/mnt/integrity_store/starling/internal"
```
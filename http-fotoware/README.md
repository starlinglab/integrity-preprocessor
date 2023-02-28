# http-fotoware

This folder contains the code for the HTTP FotoWare webhook pre and post processor. This is a web server that receives webhooks from FotoWeb and FotoPorter, verifies Root sig66 of Trust, and updates the data back into FotoWeb. It also keeps C2PA up to date.

## API

### FotoWeb Webhooks

These webhooks will check C2PA integrity and add a claim if it is changed. They will then upload the new file over FTP back to FotoWeb
- /v1/fotoware/ingestedasset
- /v1/fotoware/deletedasset
- /v1/fotoware/modifiedasset

### FotoPorter Webhooks

This webhook will extract the XML Metadata from XMP and fire a webhook to the ProvenDB/Hedera component of the PoC
- /v1/fotoware/reprocessasset

This webhook will verify Sig66, archive the original photo through the pipeline. Once pipeline is complete it will add a C2PA claim as root of trust and action-archive information. Finally, it will upload the new file into FotoWeb
- /v1/fotoware/uploadedasset

## Development

### JWTs

JWTs are not used but required as a place hold.

### .env

`JWT_SECRET` Required as a place holder  
`OUTPUT_PATH` Path to the internal folder of starling integrity  
`PORT` Port api will run on  
`FOTOWARE_API_CLIENT_ID` `FOTOWARE_API_SECRET` Fotoweb OAUTH Credentials  
`FOTOWARE_API_URL` URL to Fotowab  
`SIG66_KEY` path to sig66 keys  
`FOTOWARE_FTP_PASSWORD` FTP Password to fotoweb  

### Sig66 Format 
`preprocessor-sig66.json`

Format

```
{
  "devicename": {
    "pubKey": " "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----""
  },
  "devicename2": { 
    "pubKey": " "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----""
  }
}
```
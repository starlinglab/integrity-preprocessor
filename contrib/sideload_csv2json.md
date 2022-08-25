# sideload_csv2json

This script will convert a CSV file into a JSON index used by the preprocessor with configuration set in the `config.json` file


## .config.json
Set in the `config_filename` variable

Sample:
```json
{
    "filenameField": "FILENAME", 
    "filenameSuffix": ".jpg", 
    "org": "ABC",
    "fieldsMap": {
        "sourceId": "FILENAME",
        "description": "CAPTION"
    },
    "fieldsPrivate": [
        "SECRET_FIELD"
    ]
}
```

`filenameField`: Define field containing the filename to match for this the row's metadata.

`filenameSuffix`: If defined, value of this key will be appended to resulting `filenameField` data

`org`: Name of the org. Will be used as a key (format `{org}Metadata`) for metadata in `private` and `extras`. 

`fieldsMap`: Definition for fields that will be replaced in the `content-metadata` key

`fieldsMap`.`sourceId`: This is a special key that defined the field to be used for the `sourceId` value. Script will create a  `key`,`value` dict for `sourceId` for each item in CSV.

`fieldsPrivate`: Array of fields that will be placed in `private` instead of `extras` section

## .csv
Set as the `config_filename` variable

This is a standard CSV file

Sample:
```
FILENAME,CAPTION,SECRET_FIELD
Test1,This is a test,Shhhhh
```

## Output

Ouptut will be written to the same filename and path as the `filename` variable with the appended `.json` extension

```json
[
    {
        "filename": "Test1.jpg",
        "sourceId": {
            "key": "FILENAME",
            "value": "Test1"
        },
        "description": "This is a test",
        "meta_data_private": {
            "ABCMetadata": {
                "SECRET_FIELD": "Shhhhh"
            }
        },
        "meta_data_public": {
            "ABCMetadata": {
                "FILENAME": "Test1",
                "CAPTION": "This is a test"
            }
        }
    }
]
```
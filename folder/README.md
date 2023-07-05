# Folder Preprocessor

This preprocessor will watch a specific folder for specific extensions, then create a bundle and place it in a specific location. `env` contains only `CONFIG_FILE` that points to the json config file

## CONFIG_FILE

| Key                   | Description                                            |
| --------------------- | ------------------------------------------------------ |
| sourcePath            | path to watch for new files                            |
| targetPath            | path to place input bundles once they are completed.   |
| allowedPatterns       | extensions to watch for                                |
| extractName           | boolean - extract the name from the filename           |
| extractNameCharacters | delimiter for name extraction                          |
| method                | note about how the file arrived.                       |
| processWacz           | boolean - process metadata content from wacz files     |
| processProofMode      | boolean - process metadata content from proofmode      |
| lockFile              | wait for file not to exist before processing directory |
| author                | author metadata                                        |



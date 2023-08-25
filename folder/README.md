# Folder Preprocessor

This preprocessor will watch a specific folder for specific extensions, then create a bundle and place it in a specific location.

## preprocessor-folder.json

- sourcePath: path to watch for new files
- targetPath: path to place input bundles once they are completed. Do not include the `/input` directory
- allowedPatterns: extensions to watch
- extractName: extract the name from the filename
- extractNameCharacters: delimiter for name
- method: note about how the file arrived. Has no affect on processing but is included in the metadata.
- processWacz: process metadata content from wacz files
- processProofMode: process metadata content from proofmode
- lockFile: wait for file not to exist before processing file
- author: author metadata



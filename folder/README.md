# Folder Preprocessor

This preprocessor will watch a specific folder for specific extensions, then create a bundle and place it in a specific location.

## preprocessor-folder.json

sourcePath: path to watch for new files
targetPath: Path to place ready bundles into
allowedPatterns: Extensions to watch
extractName: Extract the name from the filename
extractNameCharacters: Delimiter for name
method: Note about how the file arrived
processWacz: Process metadata content from wacz files
processProofMode" Process metadata content from proofmode
lockFile: Wait for file not to exist before processing file
author: Author Metadata 



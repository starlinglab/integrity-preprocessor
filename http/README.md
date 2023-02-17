# http

This folder contains the code for the HTTP preprocessor, a web server that ingests data - currently only from the Starling Capture app.

## Run

First, packages must be installed, either from requirements.txt or using pipenv. After that execute the file from the parent directory: `python3 http/main.py` or `pipenv run python3 http/main.py`.

If using pipenv there is a shorcut: `pipenv run http`.

To run in debug mode, set the environement variable `HTTP_DEBUG=1`. This will disable looking for external services as required for meta-recorder, and will log client HTTP errors.

## Config

The server is configured using environment variables in a `.env` file. An example file [env.example](env.example) is provided.

The `KEYS_FILE` is path to a file of newline-separated Ethereum public keys in compressed bytes format, for example: `03aced43f9dddc120291f5cdf73580fbb592b5b21054ce61eb73cbaf98efcbe82e`. Only these keys are accepted as valid when doing cryptographic validation. If the variable is not specified then all keys will be accepted.

Empty lines and lines starting with `#` will be ignored.

## API

### create

The `create` HTTP endpoint accepts inputs for creation of C2PA claims.
* endpoint: `POST /v1/assets/create`
* request parameters:
  * authorization with a valid JWT, using the `Authorization: Bearer <JWT>` header
  * `Content-Type: multipart/form-data`
  * fields:
    * `file`: the file for which we'll create a claim; expected to be a JPG
    * `meta`: a C2PA-compliant `meta` section (JSON)
    * `signature`: a C2PA-compliant `signature` section (JSON)
    * `caption`: optional plain-text human caption of the image
  * see [example-create-request.sh](example-create-request.sh) for a working example request
 * JSON response:
   * success: `{"status": "ok", "status_code": 200}`
   * error example: `{"status": "error", "status_code": 500, "error": "<explanatory error message>"}`

Response codes follow standard HTTP conventions:
* `200 OK`: the asset is uploaded and will be processed asynchronously
* `400 Bad Request`: the request contains missing or invalid data
* `401 Unauthorized`: the JWT is missing or invalid
* `500 Internal Server Error`: the request failed due to a server error
* `503 Service Unavailable`: the service is temporarily unavailable


## Development

### JWTs

You can create a JWT on https://jwt.io/. Make sure to use the same secret you are using in your development server (the value of `JWT_SECRET`). The algorithm should be `HS256`.

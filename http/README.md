# http

This folder contains the code for the HTTP preprocessor, a web server that ingests data - currently only from the Starling Capture app.

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
* `202 Accepted`: the asset is uploaded and will be processed asynchronously
* `400 Bad Request`: the request contains missing or invalid data
* `401 Unauthorized`: the JWT is missing or invalid
* `500 Internal Server Error`: the request failed due to a server error
* `503 Service Unavailable`: the service is temporarily unavailable


## Development

### JWTs

You can create a JWT on https://jwt.io/. Make sure to use the same secret you are using in your development server (the value of `JWT_SECRET`). The algorithm should be `HS256`.

import os
import sys
import dotenv
import requests
import asyncio
import json
from aiohttp import web

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate

from contextlib import contextmanager
import shutil
import exifread
from libxmp import XMPFiles, consts # python-xmp-toolkit apt - exempi
import dotenv

dotenv.load_dotenv()

@contextmanager
def error_handling_and_response():
    """Context manager to wrap the core of a handler implementation with error handlers.
    Yields:
        response: dict containing a status and any errors encountered
    """
    response = {"status": "ok", "status_code": 200}
    try:
        yield response
    except Exception as err:
        response["error"] = f"{err}"
        response["status"] = "error"
        if isinstance(err, ClientError):
            response["status_code"] = 400
        else:
            response["status_code"] = 500
            # Print error info for unexpected errors
            print(traceback.format_exc())

####### 66 config ####
f = open('/root/.integrity/preprocessor-sig66.json')
sig66_preprocessor = json.load(f)
pubKeys = []
for device in sig66_preprocessor:
    pubKeys.append(sig66_preprocessor[device]["pubKey"])

def get_device_from_key(pubkey):
    for device in sig66_preprocessor:
        if sig66_preprocessor[device]["pubKey"] == pubkey:
            return device
    return ""

####### XMP and EXIT Stuff

def uid_from_exif(filename):
  f = open(filename, 'rb')
  tags = exifread.process_file(f)
  if "MakerNote ImageUniqueID" in tags:
    uid_bytes = tags["MakerNote ImageUniqueID"].values
    uid = ''.join(format(x, '02x') for x in uid_bytes)
    return uid
  return ""

def set_xmp_document_id(filename, uid):
    xmpfile = XMPFiles( file_path=filename, open_forupdate=True )
    xmp = xmpfile.get_xmp()
    xmp.set_property(consts.XMP_NS_XMP_MM, u'OriginalDocumentID', uid.upper())
    xmp.set_property(consts.XMP_NS_XMP_MM, u'DocumentID', uid.upper())
    xmp.set_property(consts.XMP_NS_XMP_MM, u'InstanceID', uid.upper())
    xmpfile.put_xmp(xmp)
    xmpfile.close_file()

def get_xmp_document_id(filename):

    xmpfile = XMPFiles( file_path=filename)
    xmp = xmpfile.get_xmp()
    if xmp is None:
        return ""
    if xmp.does_property_exist(consts.XMP_NS_XMP_MM, u'OriginalDocumentID') == False:
        return ""
    res = xmp.get_property(consts.XMP_NS_XMP_MM, u'OriginalDocumentID')
    xmpfile.close_file()
    return res

######## fotoware
FOTOWARE_URL = os.environ.get("FOTOWARE_API_URL")
FOTOWARE_CLIENT_ID = os.environ.get("FOTOWARE_API_CLIENT_ID")
FOTOWARE_SECRET = os.environ.get("FOTOWARE_API_SECRET")


async def fotoware_download(source_href,target):

        ## Download original image via API
        token = await fotoware_oauth(FOTOWARE_CLIENT_ID,FOTOWARE_SECRET)
        auth_header= {
            "Authorization": f"Bearer {token}",
        }

        headers = auth_header
        headers["Content-Type"] = "application/vnd.fotoware.rendition-request+json"
        headers["accept"] = "application/vnd.fotoware.rendition-response+json"

        # Request Rendition Download
        data= {"href":source_href}
        r=requests.post(f"{FOTOWARE_URL}/fotoweb/services/renditions",headers=auth_header,json=data)
        result = r.json()
        href = result["href"]
        print(f"HREF for download is at {href}")

        headers = auth_header
        r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)
        while r.status_code == 202:
            print("202... Waiting for download to be available")
            await asyncio.sleep(5)
            r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)

        with open(target, 'wb') as f:
            f.write(r.content)

async def fotoware_upload(source,filename=""):
    if filename == "":
        filename = os.path.basename(filename)
    files={filename: open(source,'rb')}

    token = await fotoware_oauth(FOTOWARE_CLIENT_ID,FOTOWARE_SECRET)
    auth_header= {
        "Authorization": f"Bearer {token}",
    }

    r=requests.post(f"{FOTOWARE_URL}/fotoweb/archives/5000-Starling/",headers=auth_header,files=files)
    result = r.json()
#    href = result["href"]

#    headers = auth_header
#    headers["accept"] = "application/vnd.fotoware.upload-status+json"
#    print (f"Downloading ... {FOTOWARE_URL}")
#    r=requests.get(f"{FOTOWARE_URL}" + href,headers=auth_header)
#    status = "pending"
#    while r.status_code == 202 or status != "done":
#        print("Waiting for upload...")
#        await asyncio.sleep(5)
#        r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)
#        res=r.json()
#        status = res["job"]["status"]
#        if status=="failed":
#            status = "done"

async def fotoware_oauth(clientid,client_secret):
    auth={
        "grant_type":"client_credentials",
        "client_id":f"{clientid}",
        "client_secret":f"{client_secret}"
    }
    print(auth)
    response=requests.post(f"{FOTOWARE_URL}/fotoweb/oauth2/token", data=auth)
    result = response.json()
    accessToken = result["access_token"]
    #accessTokenExpires = result["token_type"]
    return accessToken

async def fotoware_ingested(request):
    with error_handling_and_response() as response:
        print("Ingest Fired")
        print(request)
        print(response)

        res = await request.json()
        print(json.dumps(res))

        original_href=res["href"]
        original_filename = res["data"]["filename"]
        for rendition in res["data"]["renditions"]:
            if rendition["original"] == True:
                original_rendition=rendition["href"]
        filename=res["data"]["filename"]
        print(f"Original at  {original_rendition}")

        await fotoware_download(original_rendition,"/tmp/test.jpg")

        doc_id = get_xmp_document_id("/tmp/test.jpg")
        if doc_id != "":
            print (f"doc_id = {doc_id}  cant be a 66 image!")
            return web.json_response(response, status=response.get("status_code"))
        print("Looks ok... moving on")
        s = validate.Sig66(
            f"/tmp/test.jpg", key_list=pubKeys
        )
        res = s.validate()
        print("Validate didnt break")
        print(f"Validate is {res}")
        if res==True:
            current_device = get_device_from_key(s.public_key)
            if current_device=="":
                current_device="unknown"
            print(f"Device is {current_device}")
            uid = uid_from_exif("/tmp/test.jpg")
            print(f"UID is {uid}")
            # set xmp UUID
            set_xmp_document_id("/tmp/test.jpg",uid)
            print(f"Set XMP to UID")
            # generate filename
            extension = os.path.splitext(original_filename)[1]
            name = os.path.splitext(original_filename)[0]
            target_filename = f"{device} - {name}{extension}"
            print(f"Named {target_filename}")
            os.rename("/tmp/test.jpg",f"/tmp/{target_filename}")
            await fotoware_upload(f"/tmp/{target_filename}",target_filename)
            print(f"Named Upload Done?")
        return web.json_response(response, status=response.get("status_code"))


        print(f"Wrote to /tmp/{filename}")
        # READ 66
        data={
            "metadata": {
                "859": { "value": f"{s.auth_msg}" },
                "855": { "value": f"{s.sig}" }
            }
        }

        # Patch Metadata
        headers = auth_header
        headers["Content-Type"] = "application/vnd.fotoware.assetupdate+json"
        headers["accept"] = "application/vnd.fotoware.asset+json"
        print(original_href)
        res=requests.patch(original_href,headers=headers,json=data)
        print(res)
        print(res.content)
        print(json.dumps(data, indent=2))

        return web.json_response(response, status=response.get("status_code"))

async def fotoware_modified(request):
    with error_handling_and_response() as response:
        print("Ingest Fired")
        print(request)
        print(response)
    return web.json_response(response, status=response.get("status_code"))
async def fotoware_deleted(request):
    with error_handling_and_response() as response:
        print("Ingest Fired")
        print(request)
        print(response)
    return web.json_response(response, status=response.get("status_code"))
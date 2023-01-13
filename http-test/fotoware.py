import datetime
import os
import sys
import dotenv
import requests
import asyncio
import json
from aiohttp import web
import uuid

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate


sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import integrity_recorder_id
import common


from contextlib import contextmanager
import shutil
import exifread
from libxmp import XMPFiles, consts # python-xmp-toolkit apt - exempi
import dotenv

dotenv.load_dotenv()

integrity_path="/mnt/store/fotoware-test"
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
  """
  Extract Unique Identifier from EXIF data in a JPG
  """
  f = open(filename, 'rb')
  tags = exifread.process_file(f)
  if "MakerNote ImageUniqueID" in tags:
    uid_bytes = tags["MakerNote ImageUniqueID"].values
    uid = ''.join(format(x, '02x') for x in uid_bytes)
    return uid
  return ""
####### XMP and EXIT Stuff
def date_create_from_exif(filename):
  """
  Extract Unique Identifier from EXIF data in a JPG
  """
  f = open(filename, 'rb')
  tags = exifread.process_file(f)
  print(tags)
  if "EXIF DateTimeOriginal" in tags:
    datetime = tags["EXIF DateTimeOriginal"].values
    return datetime
  return ""
  

def set_xmp_document_id(filename, uid):
    """
    Sets a OID DID and IID XMP in a JPG
    """
    xmpfile = XMPFiles( file_path=filename, open_forupdate=True )
    xmp = xmpfile.get_xmp()
    xmp.set_property(consts.XMP_NS_XMP_MM, u'OriginalDocumentID', uid.upper())
    xmp.set_property(consts.XMP_NS_XMP_MM, u'DocumentID', uid.upper())
    xmp.set_property(consts.XMP_NS_XMP_MM, u'InstanceID', uid.upper())
    xmpfile.put_xmp(xmp)
    xmpfile.close_file()

def get_xmp_document_id(filename):
    """
    Extract OID from XMP in aJPG
    """
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
    """
    Download a file from fotoware. 

    source_href: Source url as refrenced in fotoware
    target: where to save the file
    """
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

    # Waiting for file to be ready and downloaded
    headers = auth_header
    r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)
    while r.status_code == 202:
        print("202... Waiting for download to be available")
        await asyncio.sleep(5)
        r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)

    # Save the contrent
    with open(target, 'wb') as f:
        f.write(r.content)

async def fotoware_upload(source,filename=""):
    """
    Upload a file from fotoware. 

    source: Path to file to upload
    filename: filename to be used by fotoware
    """
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
    '''
    Build oauth token
    '''
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

async def fotoware_uploaded(request):
    '''
    Process ftp uploads from fotoware, check signatures66, set OID and upload back into fotoware
    '''
    with error_handling_and_response() as response:
        print("Uploaded Fired")
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
        print(f"Original at {original_rendition}")

        tmp_uuid=uuid.uuid1()
        tmp_file = f"{integrity_path}/tmp/{tmp_uuid}.jpg"                

        await fotoware_download(original_rendition,tmp_file)

        doc_id = get_xmp_document_id(tmp_file)

        # Check Sig66
        is66="1"
        if doc_id != "":
            print (f"doc_id = {doc_id}, cant be a 66 image!")
            is66="unknown"
        
        s = validate.Sig66(
            tmp_file, key_list=pubKeys
        )        
        res = s.validate()
        print("Validate didnt break")        
        print(f"Validation is {res}")
        extension = os.path.splitext(original_filename)[1]
        name = os.path.splitext(original_filename)[0]
        target_filename = "error.jpg"

        content_metadata = common.metadata()
        content_metadata.set_mime_from_file(tmp_file)
        content_metadata.name(f"Authenticated Camera Photo")
        content_metadata.description(f"Photo uploaded through FotoWare and authenticed with Sig66")
        
        if res==True and is66 == "1" :
            sig66_meta={}
            
            current_device = get_device_from_key(s.public_key)
            if current_device=="":
                current_device="unknown"

            sig66_meta["device"]=current_device
            print(f"Device is {current_device}")
            
            uid = uid_from_exif(tmp_file)
            print(f"UID is {uid}")
            sig66_meta["exif_uid"]=uid
            # set xmp UUID            
            set_xmp_document_id(tmp_file,uid)
            print(f"Set XMP to UID")

            # generate filename
            target_filename = f"{device} - {name}{extension}"
            sig66_meta["original_filename"]=f"{name}{extension}"
            sig66_meta["target_filename"]=target_filename

            print(f"Named {target_filename}")
            os.rename(tmp_file,f"/tmp/{target_filename}")
            await fotoware_upload(f"/tmp/{target_filename}",target_filename)
            content_metadata.add_private_key({"sig66": sig66_meta})


            # Metadata component
        else:
            if res==False:
                is66 = "unverified"
            target_filename = f"{is66} - {name}{extension}"
            os.rename(tmp_file,f"/tmp/{target_filename}")
            await fotoware_upload(f"/tmp/{target_filename}",target_filename)
        
        # Starling Pipeline

        # Extract from exif?
        content_metadata.createdate_utcfromtimestamp(date_create_from_exif(tmp_file))
        asset_filename = f"/tmp/{target_filename}"
        content_metadata.validated_signature(s.validated_sigs_json())


        recorder_meta = common.get_recorder_meta("http")

        print(asset_filename)
        print( content_metadata)
        print( recorder_meta)
        print( f"{integrity_path}/tmp")
        print( f"{integrity_path}/input")

        # C2PA Inject
        await c2pa_create_claim(asset_filename,"/tmp/test123.json",content_metadata)
        out_file = common.add_to_pipeline(
            asset_filename, content_metadata.get_content(), recorder_meta, f"{integrity_path}/tmp", f"{integrity_path}/input"
        )

        print(f"{asset_filename} Created new asset {out_file}")
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

    
async def fotoware_ingested(request):
    with error_handling_and_response() as response:
        print("Ingest Fired")
        print(request)
        print(response)
    return web.json_response(response, status=response.get("status_code"))
async def fotoware_modified(request):
    with error_handling_and_response() as response:
        print("Modify Fired")
        print(request)
        print(response)
    return web.json_response(response, status=response.get("status_code"))

async def fotoware_deleted(request):
    with error_handling_and_response() as response:
        print("Delete Fired")
        print(request)
        print(response)
    return web.json_response(response, status=response.get("status_code"))

def _get_index_by_label(c2pa, label):
    return [i for i, o in enumerate(c2pa["assertions"]) if o["label"] == label][0]

async def c2pa_create_claim(source_file,target_file,content_metadata): 
    print("====================STARTING CLAIM===========================")
    with open("/root/dev/integrity-preprocessor/http-test/template/c2pa_template.json") as c2pa_template_handle:
        c2pa_1= json.load(c2pa_template_handle)
        c2pa_1["claim_generator"] = "Sig66"

        # Insert authorship information
        m = _get_index_by_label(c2pa_1, "stds.schema-org.CreativeWork")
        c2pa_1["assertions"][m]["data"]["author"][0]["@type"] = content_metadata.get("author").get("@type")
        c2pa_1["assertions"][m]["data"]["author"][0]["identifier"] = content_metadata.get("author").get("identifier")
        c2pa_1["assertions"][m]["data"]["author"][0]["name"] = content_metadata.get("author").get("name")        

        # Insert c2pa.created actions
        m = _get_index_by_label(c2pa_1, "c2pa.actions")
        n = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.created"][0]
        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = content_metadata.get("dateCreate")

        # Insert identifier
        m = _get_index_by_label(c2pa_1, "org.starlinglab.integrity")
        content_id_starling_capture = content_metadata.get("private", {}).get("starlingCapture", {}).get("metadata", {}).get("proof", {}).get("hash")
        if content_id_starling_capture:
            ## OID
            c2pa_1["assertions"][m]["data"]["starling:identifier"] = content_id_starling_capture

        # Insert signatures
        c2pa_1["assertions"][m]["data"]["starling:signatures"] = []
        for sig in content_metadata.get("validatedSignatures", []):
            x = {}
            if sig.get("provider"): x["starling:provider"] = sig.get("provider")
            if sig.get("algorithm"): x["starling:algorithm"] = sig.get("algorithm")
            if sig.get("publicKey"): x["starling:publicKey"] = sig.get("publicKey")
            if sig.get("signature"): x["starling:signature"] = sig.get("signature")
            if sig.get("authenticatedMessage"): x["starling:authenticatedMessage"] = sig.get("authenticatedMessage")
            if sig.get("authenticatedMessageDescription"): x["starling:authenticatedMessageDescription"] = sig.get("authenticatedMessageDescription")
            if sig.get("custom"): x["starling:custom"] = sig.get("custom")
            c2pa_1["assertions"][m]["data"]["starling:signatures"].append(x)

        with open(f"{source_file}.json", "w") as man:
            json.dump(c2pa_1, man)
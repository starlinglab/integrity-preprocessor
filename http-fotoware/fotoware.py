import time
import threading
import subprocess
import datetime
import os
import sys
import dotenv
import requests
import asyncio
import json
from aiohttp import web
import uuid
import ftplib
import traceback

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate
import integrity_recorder_id
import common


from contextlib import contextmanager
import shutil
import exifread
from libxmp import XMPFiles, consts # python-xmp-toolkit apt - exempi
import dotenv

class ClientError(Exception):
    # Raised to trigger status code 400 responses
    pass

logging = common.logging
logging.info("Started folder preprocessor")


dotenv.load_dotenv()

integrity_path="/mnt/integrity_store/starling/internal/reuters/test-collection"
http_webhook_xmp = "http://169.55.166.2:3000/jpeg-data"

if not os.path.exists(f"{integrity_path}/tmp"):
    os.mkdir(f"{integrity_path}/tmp")
if not os.path.exists(f"{integrity_path}/tmp/source"):
    os.mkdir(f"{integrity_path}/tmp/source")
if not os.path.exists(f"{integrity_path}/input"):
    os.mkdir(f"{integrity_path}/input")
if not os.path.exists(f"{integrity_path}/c2pa"):
    os.mkdir(f"{integrity_path}/c2pa")

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
  if "EXIF DateTimeOriginal" in tags:
    original_date_time = tags["EXIF DateTimeOriginal"].values
    original_date_timestamp = datetime.datetime.strptime(original_date_time,"%Y:%m:%d %H:%M:%S").timestamp()
    return original_date_timestamp
  return ""

######## Add Starling Signature into XMP
def set_xmp_signatures(filename, signature):
    """
    Create a new starling namespace in XMP and load signature into it
    """
    logging.info(f"set_xmp_signatures - Adding signatures so {filename}")
    const_xmp_starling = "http://starlinglab.org/integrity/signatures"
    xmpfile = XMPFiles( file_path=filename, open_forupdate=True )
    xmp = xmpfile.get_xmp()
    xmp.register_namespace(const_xmp_starling,"starling")
    xmp.set_property(const_xmp_starling, u'StarlingAlgorithm', signature["algorithm"])
    xmp.set_property(const_xmp_starling, u'StarlingAuthenticatedMessage', signature["authenticatedMessage"])
    xmp.set_property(const_xmp_starling, u'StarlingAuthenticatedMessageDescription', signature["authenticatedMessageDescription"])
    xmp.set_property(const_xmp_starling, u'StarlingProvider', signature["provider"])
    xmp.set_property(const_xmp_starling, u'StarlingPublicKey', signature["publicKey"])
    xmp.set_property(const_xmp_starling, u'StarlingSignature', signature["signature"])
    xmpfile.put_xmp(xmp)
    xmpfile.close_file()

######## Setup XMP ODID
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


##### Get XMP ODID
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

def get_xmp_photoshop_history(filename):
    xmpfile = XMPFiles( file_path=filename)

    xmp = xmpfile.get_xmp()
    XMP_NS_PHOTOSHOP = "http://ns.adobe.com/photoshop/1.0/"
    if xmp.does_property_exist(XMP_NS_PHOTOSHOP,u'History'):
        return xmp.get_property(XMP_NS_PHOTOSHOP,u'History')


######## fotoware
FOTOWARE_URL = os.environ.get("FOTOWARE_API_URL")
FOTOWARE_CLIENT_ID = os.environ.get("FOTOWARE_API_CLIENT_ID")
FOTOWARE_SECRET = os.environ.get("FOTOWARE_API_SECRET")
FOTOWARE_IP_ADDRESS = "52.166.150.145"
FOTOWARE_FTP_PASSWORD = os.environ.get("FOTOWARE_FTP_PASSWORD")
C2PA_PATH = os.environ.get("C2PA_PATH", "/dev/null")

### Fotoware Download 
def fotoware_download(source_href,target):
    """
    Download a file from fotoware.

    source_href: Source url as refrenced in fotoware
    target: where to save the file
    """
    ## Download original image via API
    token = fotoware_oauth(FOTOWARE_CLIENT_ID,FOTOWARE_SECRET)
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
    logging.info(f"fotoware_download - Fotoware URL is {href}")

    # Waiting for file to be ready and downloaded
    headers = auth_header
    r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)
    while r.status_code == 202:
        logging.info(f"fotoware_download - Waiting for download request to be available (202)")
        time.sleep(3)
        r=requests.get(f"{FOTOWARE_URL}/" + href,headers=auth_header)

    # Save the contrent
    with open(target, 'wb') as f:
        f.write(r.content)

### Fotoware Upload
def fotoware_upload(source,filename=""):
    """
    Upload a file from fotoware.

    source: Path to file to upload
    filename: filename to be used by fotoware
    """
    logging.info(f"fotoware_upload - Uploading {filename} via API")

    shutil.copyfile(source,f"/tmp/{filename}")    
    new_source=f"/tmp/{filename}"

    if filename == "":
        filename = os.path.basename(filename)
    files={filename: open(new_source,'rb')}

    token = fotoware_oauth(FOTOWARE_CLIENT_ID,FOTOWARE_SECRET)
    auth_header= {
        "Authorization": f"Bearer {token}",
    }

    r=requests.post(f"{FOTOWARE_URL}/fotoweb/archives/5000-Starling/",headers=auth_header,files=files)  


### Fotoware oauth
def fotoware_oauth(clientid,client_secret):
    '''
    Build oauth token
    '''
    auth={
        "grant_type":"client_credentials",
        "client_id":f"{clientid}",
        "client_secret":f"{client_secret}"  
    }
    logging.info(f"fotoware_oauth - Generating oauth")    
    response=requests.post(f"{FOTOWARE_URL}/fotoweb/oauth2/token", data=auth)
    result = response.json()
    accessToken = result["access_token"]
    #accessTokenExpires = result["token_type"]
    return accessToken

#### Upload Thread
def fotoware_uploaded_thread(res):
    logging.info(f"fotoware_uploaded_thread - Starting") 

    
    original_rendition = ""
    original_filename = res["data"]["filename"]
    for rendition in res["data"]["renditions"]:
        if rendition["original"] == True:
            original_rendition=rendition["href"]
    logging.info(f"fotoware_uploaded_thread - Fotoware URL at {original_rendition}") 

    extension = os.path.splitext(original_filename)[1]
    name = os.path.splitext(original_filename)[0]

    tmp_uuid=uuid.uuid1()
    tmp_file = f"{integrity_path}/tmp/{tmp_uuid}.jpg"
    tmp_file_orig = f"{tmp_file}.orig.jpg"
    
    fotoware_download(original_rendition,tmp_file)
  
    shutil.copyfile(tmp_file,tmp_file_orig)
    doc_id = get_xmp_document_id(tmp_file)

    # Check Sig66
    is66="1"
    if doc_id != "":
        logging.info(f"fotoware_uploaded_thread - doc_id = {doc_id}, cant be a 66 image!")
        is66="unknown"
    s = None
    if is66=="1":            
        s = validate.Sig66(
            tmp_file, key_list=pubKeys
        )            
        try:
            res = s.validate()
            logging.info(f"fotoware_uploaded_thread - Validated Sig66")
        except:
            logging.info(f"fotoware_uploaded_thread - Validation Broken Sig66")
            # Perform Error Here         

    # Start Metadata object
    content_metadata = common.Metadata()
    content_metadata.set_mime_from_file(tmp_file)
    content_metadata.name(f"Authenticated Camera Photo")
    content_metadata.description(f"Photo uploaded through FotoWare and authenticated with Sig66")


    reuters_author = {
        "@type": "Organization",
        "identifier": "https://www.reuters.com/",
        "name": "Reuters"
    }
    content_metadata.author(reuters_author)

    target_local_file = "" #C2PA Target
    target_filename = "error.jpg"

    # Save metadata info
    uid = "undefined"
    current_device = "undefined"
    if res==True and is66 == "1" :
        sig66_meta={}
        
        # Deal with sig66 metadata
        current_device = get_device_from_key(s.public_key)
        if current_device=="":
            current_device="unknown"
        logging.info(f"fotoware_uploaded_thread - Device used {current_device}")
        sig66_meta["device"]=current_device

        # Deal with file nameing
        uid = uid_from_exif(tmp_file)

        # generate filename
        target_filename = f"{current_device} - {name}{extension.lower()}"

        sig66_meta["original_filename"]=f"{name}{extension}"
        sig66_meta["target_filename"]=target_filename

        # Set the UUID to XMP
        sig66_meta["exif_uid"]=uid
        # set xmp UUID
        set_xmp_document_id(tmp_file,uid)
        content_metadata.set_source_id("odid",uid)        
        logging.info(f"fotoware_uploaded_thread - XMP OID is set to UID of {uid}")

        content_metadata.add_private_key({"reuters_vs": sig66_meta})
        signatures = s.validated_sigs_json()
        content_metadata.validated_signature(s.validated_sigs_json())        
        set_xmp_signatures(tmp_file,signatures[0])
        logging.info(f"fotoware_uploaded_thread - XMP Signatures Saved")

        # Metadata component
    else:
        if res==False:
            current_device = "unverified"
            uid = uid_from_exif(tmp_file)
            # Todo - set one if its not set
            set_xmp_document_id(tmp_file,uid)
            logging.info(f"fotoware_uploaded_thread - Device is not verified")

    target_filename = f"{current_device} - {name}{extension.lower()}"
    target_local_file = f"{uid.upper()}{extension.lower()}"
    ts=get_utc_timestmap()
    target_local_file_ts = f"{uid.upper()}-{ts}{extension.lower()}"
    target_local_file_root = f"{uid.upper()}-root{extension.lower()}"
    logging.info(f"Setting {uid.upper()} to  {ts}")

    # Extract from exif?
    date_create_exif = date_create_from_exif(tmp_file)
    logging.info(f"fotoware_uploaded_thread - EXIF Date Captures is {date_create_exif}")
    content_metadata.createdate_utcfromtimestamp(date_create_exif)
    logging.info(f"fotoware_uploaded_thread - MetaData Captured Date is now {content_metadata._content['dateCreated']}")

    recorder_meta = common.get_recorder_meta("http")

    logging.info(f"fotoware_uploaded_thread - Sending to Pipeline")
    out_file = common.add_to_pipeline(
        tmp_file_orig, content_metadata.get_content(), recorder_meta, f"{integrity_path}/tmp", f"{integrity_path}/input"
    )
    logging.info(f"fotoware_uploaded_thread - Pipeline file at {out_file}")

    # Get blockchain commits
    receipt_path,filename =  os.path.split(out_file)
    receipt_path = receipt_path.replace("/internal/","/shared/")
    receipt_path = os.path.split(receipt_path)[0] + "/action-archive"
    filename = os.path.splitext(filename)[0] + ".json"
    receipt_path = f"{receipt_path}/{filename}"
    logging.info(f"fotoware_uploaded_thread - Waiting for pipeline to finish")
    while not os.path.exists(receipt_path):
        print(".",end = '')
        time.sleep(3) 
    print("+")

    logging.info(f"fotoware_uploaded_thread - Reading receipt file from {receipt_path}")
    f=open(receipt_path,"r")
    receipt= json.load(f)

    logging.info(f"fotoware_uploaded_thread - Creating inital C2PA Claim")
    target_file_location_path = f"{integrity_path}/c2pa/"

    c2pa_create_claim(tmp_file,f"{target_file_location_path}{target_local_file_ts}",content_metadata.get_content(),receipt,target_filename)
    logging.info(f"Saving at {target_local_file} and {target_local_file_root}")
    shutil.copy2(f"{target_file_location_path}{target_local_file_ts}",f"{target_file_location_path}/{target_local_file}")
    shutil.copy2(f"{target_file_location_path}{target_local_file_ts}",f"{target_file_location_path}/{target_local_file_root}")

    logging.info(f"fotoware_uploaded_thread - Uploading file to Fotoware archive")
    fotoware_upload(f"{target_file_location_path}{target_local_file}",target_filename)        
   
    logging.info(f"fotoware_uploaded_thread - Success")

async def fotoware_uploaded(request):
    '''
    Process ftp uploads from fotoware, check signatures66, set OID and upload back into fotoware
    '''
    with error_handling_and_response() as response:
        logging.info(f"fotoware_uploaded - Start")         
        logging.info(f"fotoware_uploaded - Spawning Thread") 
        
        #loop = asyncio.get_running_loop()
        #tsk = loop.create_task(fotoware_uploaded_thread(request))

        #loop = asyncio.get_running_loop()
        #tsk = loop.create_task(fotoware_uploaded_thread(request))
        # threading.Thread(target=fotoware_uploaded_thread,args=(request))        

        res  = await request.json()
        threading.Thread(target=fotoware_uploaded_thread,args=[res]).start()

        logging.info(f"fotoware_uploaded - returning 200") 
        return web.json_response(response, status=response.get("status_code"))


def check_photo_for_c2pa(res,action):

    #res = await request.json()
    original_rendition = ""

    # Check where the latest metadata from fotoweb is
    asset =res["data"]
    if "asset" in res["data"]:
        asset=res["data"]["asset"]
        logging.info(f"check_photo_for_c2pa - Using asset key")


    original_filename = asset["filename"]

    for rendition in asset["renditions"]:
        if rendition["original"] == True:
            original_rendition=rendition["href"]

    logging.info(f"check_photo_for_c2pa - Fotoware URL at {original_rendition}")
    tmp_uuid=uuid.uuid1()
    tmp_file = f"{integrity_path}/tmp/{tmp_uuid}.jpg"

    logging.info(f"check_photo_for_c2pa - Downloading from Fotoware to {tmp_file}")
    fotoware_download(original_rendition,tmp_file)

    logging.info(f"check_photo_for_c2pa - Checking C2PA integrity")
    if c2pa_validate(tmp_file) == True:
        logging.info(f"check_photo_for_c2pa - C2PA intact, skipping injection")
        return
            
    # Extract OID and define last c2pa injection
    OID = get_xmp_document_id(tmp_file)    
    LASTC2PA = f"{integrity_path}/c2pa/{OID.upper()}.jpg"
    ts = get_utc_timestmap()
    THISC2PA = f"{integrity_path}/c2pa/{OID.upper()}-{ts}.jpg"

    # reprocess - fire webhook
    if action=="reprocess":
        xmpfile = XMPFiles( file_path=tmp_file)
        xmp = xmpfile.get_xmp()
        XMP_NS_PHOTOSHOP = "http://ns.adobe.com/photoshop/1.0/"
        if xmp.does_property_exist(XMP_NS_PHOTOSHOP,u'History'):
            jpeg_data = { "data" : xmp.get_property(XMP_NS_PHOTOSHOP,u'History') }
            jpeg_data["odid"] = OID
            logging.info(f"check_photo_for_c2pa - Posting JPEG_DATA to Hedera")
            requests.post(http_webhook_xmp,json=jpeg_data)
            logging.info(f"check_photo_for_c2pa - Post complete")

    logging.info(f"check_photo_for_c2pa - Signing changes since {LASTC2PA}")
    target_path=f"{integrity_path}/tmp/{original_filename}"
    c2pa_fotoware_update(LASTC2PA,tmp_file,target_path,action,None)
    upload_to_ftp(target_path)
    logging.info(f"check_photo_for_c2pa - Coping new C2PA file to {LASTC2PA}")
    os.unlink(LASTC2PA)
    os.rename(target_path, LASTC2PA)

    # Copy versioned as well
    shutil.copy2(LASTC2PA,THISC2PA)

def get_utc_timestmap():
    dt = datetime.datetime.now(datetime.timezone.utc)  
    utc_time = dt.replace(tzinfo=datetime.timezone.utc)
    utc_timestamp = utc_time.timestamp()
    return str(utc_timestamp).split(".")[0]

async def fotoware_reprocess(request):
    with error_handling_and_response() as response:
        logging.info(f"fotoware_reprocess - Starting")

        #loop = asyncio.get_running_loop()
        #tsk = loop.create_task(check_photo_for_c2pa(request,"reprocess"))  

        res  = await request.json()
        threading.Thread(target=check_photo_for_c2pa,args=[res,"reprocess"]).start()


        

#        print(request)
#        print(response)
        return web.json_response(response, status=response.get("status_code"))

async def fotoware_finalize(request):
    with error_handling_and_response() as response:
        logging.info(f"fotoware_finalize - Starting")

        #loop = asyncio.get_running_loop()
        #tsk = loop.create_task(check_photo_for_c2pa(request,"finalize"))  

        res  = await request.json()
        threading.Thread(target=check_photo_for_c2pa,args=[res,"finalize"]).start()

#        print(request)
#        print(response)
        return web.json_response(response, status=response.get("status_code"))


async def fotoware_ingested(request):
    with error_handling_and_response() as response:
        
        #loop = asyncio.get_running_loop()
        #tsk = loop.create_task(check_photo_for_c2pa(request,"ingested"))

        res  = await request.json()
        threading.Thread(target=check_photo_for_c2pa,args=[res,"ingested"]).start()

    return web.json_response(response, status=response.get("status_code"))

async def fotoware_modified(request):
    with error_handling_and_response() as response:
        logging.info(f"fotoware_modified - Starting")
        #loop = asyncio.get_running_loop()        
        #tsk = loop.create_task(check_photo_for_c2pa(request,"modified"))        

        res  = await request.json()
        threading.Thread(target=check_photo_for_c2pa,args=[res,"modified"]).start()

        

    return web.json_response(response, status=response.get("status_code"))

async def fotoware_deleted(request):
    with error_handling_and_response() as response:
        logging.info(f"fotoware_modified - Starting")        
#        print(request)
#        print(response)
    return web.json_response(response, status=response.get("status_code"))

#-------
def _get_index_by_label(c2pa, label):
    return [i for i, o in enumerate(c2pa["assertions"]) if o["label"] == label][0]

def c2pa_create_claim(source_file,target_file,content_metadata,receipt_json,filename):

    logging.info(f"c2pa_create_claim - {source_file} => {target_file}")

    with open("/root/integrity-preprocessor/http-fotoware/template/c2pa_template.json") as c2pa_template_handle:
        c2pa_1= json.load(c2pa_template_handle)
        c2pa_1["title"] = os.path.basename(filename)
        c2pa_1["claim_generator"] = "Starling_Integrity"

        # Insert authorship information
        m = _get_index_by_label(c2pa_1, "stds.schema-org.CreativeWork")
        c2pa_1["assertions"][m]["data"]["author"][0]["@type"] = content_metadata.get("author").get("@type")
        c2pa_1["assertions"][m]["data"]["author"][0]["identifier"] = content_metadata.get("author").get("identifier")
        c2pa_1["assertions"][m]["data"]["author"][0]["name"] = content_metadata.get("author").get("name")

        # Insert c2pa.created actions
        m = _get_index_by_label(c2pa_1, "c2pa.actions")
        n = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.created"][0]
        create_date = content_metadata.get("dateCreated")
        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = create_date

        # Insert identifier
        m = _get_index_by_label(c2pa_1, "org.starlinglab.integrity")
        content_id_starling_capture = content_metadata.get("private", {}).get("reuters_v2", {}).get("exif_uid")
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

        # Insert Blockchain Registartion
        c2pa_1["assertions"][m]["data"]["starling:archives"].append(receipt_json)

        with open(f"{source_file}.json", "w") as man:
            json.dump(c2pa_1, man)
        p_c2patool = C2PA_PATH
        
        tmp_file="/tmp/" + filename  
        shutil.copyfile(source_file,tmp_file)
        
        args= [f"{p_c2patool}", 
            f"{tmp_file}", 
            "--manifest", f"{source_file}.json", 
            "--output" , f"{target_file}", 
            "--force"]
        p = subprocess.run(args, capture_output=True)
        logging.info(f"c2pa_create_claim - Ran {args}")
        
        #print([f"{p_c2patool}", f"{source_file}", "--manifest", f"{source_file}.json", "--output" , f"{target_file}", "--force"])
        logging.info(f"c2pa_create_claim - Complete - {target_file}")


def c2pa_validate(source_file):
    p_c2patool = C2PA_PATH
    p = subprocess.run([f"{p_c2patool}", "--info", f"{source_file}"], capture_output=True)
    for line in p.stdout.decode("utf-8").split("\n"):
        if line=="Validated":
            return True
        if line=="Validation issues:":
            return False
    return False

def c2pa_fotoware_update(lastC2PA, current_file, filename,webhook_action,history):
    logging.info(f"c2pa_fotoware_update - {lastC2PA} + {current_file} => {filename}")

    tmp_source_path=f"{integrity_path}/tmp/source/{os.path.basename(filename)}"
    shutil.copyfile(lastC2PA,tmp_source_path)

    json_file=""
    action="c2pa.managed"

    source = "fotoware"
    if webhook_action == "reprocess":
        source="photoshop"

    if source=="fotoware":
        json_file = "/root/integrity-preprocessor/http-fotoware/template/c2pa_fotoware.json"
        action = "c2pa.managed"
    if source=="photoshop":
        json_file = "/root/integrity-preprocessor/http-fotoware/template/c2pa_photoshop.json"
        action = "c2pa.edited"

    with open(json_file) as c2pa_template_handle:
        c2pa_1= json.load(c2pa_template_handle)
        c2pa_1["title"] = os.path.basename(filename)

        # Insert c2pa.created actions
        m = _get_index_by_label(c2pa_1, "c2pa.actions")
        n = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == action][0]
        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = datetime.datetime.now().isoformat()
        c2pa_1["assertions"][m]["data"]["actions"][n]["history"] = history

        with open(f"{lastC2PA}.json", "w") as man:
            json.dump(c2pa_1, man)
        p_c2patool = C2PA_PATH
        p = subprocess.run([f"{p_c2patool}", 
                    f"{current_file}", 
                    "--manifest", f"{lastC2PA}.json", 
                    "--output" , f"{filename}", 
                    "-p",f"{tmp_source_path}"]
                , capture_output=True)
        args=[f"{p_c2patool}", f"{current_file}", "--manifest", f"{lastC2PA}.json", "--output" , f"{filename}", "-p",f"{lastC2PA}"]
        p = subprocess.run(args, capture_output=True)
        logging.info(f"c2pa_fotoware_update - Ran {args}")
        logging.info(f"c2pa_create_claim - Complete - {current_file}")        

        
def upload_to_ftp(source):
    logging.info(f"upload_to_ftp - Staring Session")
    session = ftplib.FTP('site1.fotoware.it','starling',str(FOTOWARE_FTP_PASSWORD))
    source_name=os.path.basename(source)
    try:
        fileexists = session.size(source_name)
        logging.info(f"upload_to_ftp - Deleting File  {source_name}")
        session.delete(source_name)
    except:
        logging.info(f"upload_to_ftp - File missing {source_name}. Skipping delete")

    logging.info(f"upload_to_ftp - Uploading to FTP {source_name}")
    file = open(source,'rb')                  # file to send
    session.storbinary(f"STOR {source_name}", file)     # send the file
    file.close()
    session.quit()
    logging.info(f"upload_to_ftp - Complete")

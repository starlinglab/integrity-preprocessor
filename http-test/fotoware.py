
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

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../lib")
import validate
import integrity_recorder_id
import common


from contextlib import contextmanager
import shutil
import exifread
from libxmp import XMPFiles, consts # python-xmp-toolkit apt - exempi
import dotenv

dotenv.load_dotenv()

integrity_path="/mnt/integrity_store/starling/internal/reuters/test-collection"
if not os.path.exists(f"{integrity_path}/tmp"):
    os.mkdir(f"{integrity_path}/tmp")
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

def set_xmp_signatures(filename, signature):
    """
    Create a new starling namespace in XMP and load signature into it
    """
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
FOTOWARE_IP_ADDRESS = "52.166.150.145"


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
        await asyncio.sleep(3)
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
    print(f"Uploafing {filename}")

    shutil.copyfile(source,f"/tmp/{filename}")
    
    new_source=f"/tmp/{filename}"

    if filename == "":
        filename = os.path.basename(filename)
    files={filename: open(new_source,'rb')}

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
#    print(auth)
    response=requests.post(f"{FOTOWARE_URL}/fotoweb/oauth2/token", data=auth)
    result = response.json()
    accessToken = result["access_token"]
    #accessTokenExpires = result["token_type"]
    return accessToken

fotoware_lock={}
async def fotoware_uploaded(request):
    '''
    Process ftp uploads from fotoware, check signatures66, set OID and upload back into fotoware
    '''
    with error_handling_and_response() as response:
        print("====================================Uploaded Fired===================================")
#        print(request)
#        print(response)

        res = await request.json()
#        print(json.dumps(res))

        # Download the file
        original_rendition = ""
        original_filename = res["data"]["filename"]
        for rendition in res["data"]["renditions"]:
            if rendition["original"] == True:
                original_rendition=rendition["href"]
        print(f"Original at {original_rendition}")

        extension = os.path.splitext(original_filename)[1]
        name = os.path.splitext(original_filename)[0]

        # Code to prevent webhook timing out and fireing twice
        if name in fotoware_lock:
            print(f"{name} Already processing.. returning complete to webhook so it doesnt process twice")
            return web.json_response(response, status=response.get("status_code"))
        fotoware_lock[name]=1



        tmp_uuid=uuid.uuid1()
        tmp_file = f"{integrity_path}/tmp/{tmp_uuid}.jpg"
        tmp_file_orig = f"{tmp_file}.orig.jpg"
        

        await fotoware_download(original_rendition,tmp_file)

        shutil.copyfile(tmp_file,tmp_file_orig)
        doc_id = get_xmp_document_id(tmp_file)

        # Check Sig66
        is66="1"
        if doc_id != "":
            print (f"doc_id = {doc_id}, cant be a 66 image!")
            is66="unknown"
        s = None
        if is66=="1":
            print("Validating Sig66")
            s = validate.Sig66(
                tmp_file, key_list=pubKeys
            )
            try:
                res = s.validate()
            except:
                print("Validation Broken")
                return web.json_response(response, status=response.get("status_code"))
            print("Validate complete")
            print(s.validated_sigs_json())
       


        # Start Metadata object
        content_metadata = common.Metadata()
        content_metadata.set_mime_from_file(tmp_file)
        content_metadata.name(f"Authenticated Camera Photo")
        content_metadata.description(f"Photo uploaded through FotoWare and authenticed with Sig66")

        target_local_file = "" #C2PA Target
        target_filename = "error.jpg"

        # Save metadata info
        if res==True and is66 == "1" :
            sig66_meta={}
            
            # Deal with sig66 metadata
            current_device = get_device_from_key(s.public_key)
            if current_device=="":
                current_device="unknown"

            sig66_meta["device"]=current_device
            print(f"Device is {current_device}")

            # Deal with file nameing
            uid = uid_from_exif(tmp_file)

            # generate filename
            target_filename = f"{current_device} - {name}{extension.lower()}"
            target_local_file = f"{uid.upper()}{extension.lower()}"

            sig66_meta["original_filename"]=f"{name}{extension}"
            sig66_meta["target_filename"]=target_filename

          
            # Set the UUID to XMP
            print(f"UID is {uid}")
            sig66_meta["exif_uid"]=uid
            # set xmp UUID
            set_xmp_document_id(tmp_file,uid)
            print(f"Set XMP to UID")

            content_metadata.add_private_key({"sig66": sig66_meta})
            signatures = s.validated_sigs_json()
            print(signatures)
            content_metadata.validated_signature(s.validated_sigs_json())
            set_xmp_signatures(tmp_file,signatures[0])

            # Metadata component
        else:
            if res==False:
                current_device = "unverified"
                target_filename = f"{current_device} - {name}{extension.lower()}"
                uid = uid_from_exif(tmp_file)
                target_local_file = f"{uid.upper()}{extension.lower()}"         
                set_xmp_document_id(tmp_file,uid)


        # Extract from exif?
        date_create_exif = date_create_from_exif(tmp_file)
        content_metadata.createdate_utcfromtimestamp(date_create_exif)

        recorder_meta = common.get_recorder_meta("http")

#        print(original_file)
#        print( content_metadata)
#        print( recorder_meta)
#        print( f"{integrity_path}/tmp")
#        print( f"{integrity_path}/input")
#        print( f"{integrity_path}/c2pa")

        out_file = common.add_to_pipeline(
            tmp_file_orig, content_metadata.get_content(), recorder_meta, f"{integrity_path}/tmp", f"{integrity_path}/input"
        )

        # Get blockchain commits
        receipt_path,filename =  os.path.split(out_file)
        receipt_path = receipt_path.replace("/internal/","/shared/")
        receipt_path = os.path.split(receipt_path)[0] + "/action-archive"
        filename = os.path.splitext(filename)[0] + ".json"
        receipt_path = f"{receipt_path}/{filename}"
        print(f"=====Waiting for {receipt_path}===========")
        while not os.path.exists(receipt_path):
            print("....")
            await asyncio.sleep(3)
        f=open(receipt_path,"r")
        receipt= json.load(f)

        await c2pa_create_claim(tmp_file,f"{integrity_path}/c2pa/{target_local_file}",content_metadata.get_content(),receipt,target_filename)

        print(f"Uploading ")
        await fotoware_upload(f"{integrity_path}/c2pa/{target_local_file}",target_filename)        

        print(f"----------------{name} Created new asset {out_file}-----------------")

        del fotoware_lock[name]        

        return web.json_response(response, status=response.get("status_code"))


async def check_photo_for_c2pa(request):

    res = await request.json()
    print(res)
    original_rendition = ""

    asset =res["data"]

    if "asset" in res["data"]:
        asset=res["data"]["asset"]
        print("Selecting ASSET Tag")

    original_filename = asset["filename"]

    for rendition in asset["renditions"]:
        if rendition["original"] == True:
            original_rendition=rendition["href"]

    print(f"Original at {original_rendition}")

    tmp_uuid=uuid.uuid1()
    tmp_file = f"{integrity_path}/tmp/{tmp_uuid}.jpg"

    await fotoware_download(original_rendition,tmp_file)
    if c2pa_validate(tmp_file) == True:
        print("C2PA Intact, Skipping file")
            
    # Extract OID
    OID = get_xmp_document_id(tmp_file)
    LASTC2PA = f"{integrity_path}/c2pa/{OID.upper()}.jpg"
    target_path=f"{integrity_path}/tmp/{original_filename}"
    c2pa_fotoware_update(LASTC2PA,tmp_file,target_path)
    upload_to_ftp(target_path)
    os.unlink(LASTC2PA)
    os.rename(target_path, LASTC2PA)


async def fotoware_ingested(request):
    with error_handling_and_response() as response:
        print("Ingest Fired")
#        print(request)
#        print(response)
        await check_photo_for_c2pa(request)
    return web.json_response(response, status=response.get("status_code"))
async def fotoware_modified(request):
    with error_handling_and_response() as response:
        print("=====================================Modify Fired============================")
#        print(response)
        await check_photo_for_c2pa(request)
    return web.json_response(response, status=response.get("status_code"))

async def fotoware_deleted(request):
    with error_handling_and_response() as response:
        print("Delete Fired")
#        print(request)
#        print(response)
    return web.json_response(response, status=response.get("status_code"))

#-------
def _get_index_by_label(c2pa, label):
    return [i for i, o in enumerate(c2pa["assertions"]) if o["label"] == label][0]

async def c2pa_create_claim(source_file,target_file,content_metadata,receipt_json,filename):

    print("====================STARTING CLAIM===========================")
    print(f"Source {source_file} ")
    print(f"Target {target_file} ")

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
        create_date = content_metadata.get("dateCreated")
        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = create_date

        # Insert identifier
        m = _get_index_by_label(c2pa_1, "org.starlinglab.integrity")
        content_id_starling_capture = content_metadata.get("private", {}).get("sig66", {}).get("exif_uid")
        if content_id_starling_capture:
            ## OID
            c2pa_1["assertions"][m]["data"]["starling:identifier"] = content_id_starling_capture

        # Insert signatures
        c2pa_1["assertions"][m]["data"]["starling:signatures"] = []
        for sig in content_metadata.get("validatedSignature", []):
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
        p_c2patool = "/root/.cargo/bin/c2patool"

        
        tmp_file="/tmp/" + filename        
        p = subprocess.run([f"{p_c2patool}", f"{source_file}", "--manifest", f"{source_file}.json", "--output" , f"{tmp_file}", "--force"], capture_output=True)        
        shutil.copyfile(tmp_file,target_file)

        print([f"{p_c2patool}", f"{source_file}", "--manifest", f"{source_file}.json", "--output" , f"{target_file}", "--force"])
        print(f"C2PA FILE AT {target_file}")


def c2pa_validate(source_file):
    p_c2patool = "/root/.cargo/bin/c2patool"
    p = subprocess.run([f"{p_c2patool}", "--info", f"{source_file}"], capture_output=True)
    for line in p.stdout.decode("utf-8").split("\n"):
        if line=="Validated":
            return True
        if line=="Validation issues:":
            return False
    return False

def c2pa_fotoware_update(lastC2PA, current_file, filename):

    with open("/root/dev/integrity-preprocessor/http-test/template/c2pa_fotoware.json") as c2pa_template_handle:
        c2pa_1= json.load(c2pa_template_handle)
        c2pa_1["claim_generator"] = "Fotoware"
        
        # Insert c2pa.created actions
        m = _get_index_by_label(c2pa_1, "c2pa.actions")
        n = [i for i, o in enumerate(c2pa_1["assertions"][m]["data"]["actions"]) if o["action"] == "c2pa.managed"][0]
        c2pa_1["assertions"][m]["data"]["actions"][n]["when"] = datetime.datetime.now().isoformat()

        with open(f"{lastC2PA}.json", "w") as man:
            json.dump(c2pa_1, man)
        p_c2patool = "/root/.cargo/bin/c2patool"
        p = subprocess.run([f"{p_c2patool}", f"{current_file}", "--manifest", f"{lastC2PA}.json", "--output" , f"{filename}", "-p",f"{lastC2PA}"], capture_output=True)
        print([f"{p_c2patool}", f"{current_file}", "--manifest", f"{lastC2PA}.json", "--output" , f"{filename}", "-p",f"{lastC2PA}"])
        print(p)
        print(f"C2PA FILE AT {current_file}")

        
def upload_to_ftp(source):
    session = ftplib.FTP('site1.fotoware.it','starling','3kfsP4#Q')
    source_name=os.path.basename(source)
    try:
        fileexists = session.size(source_name)
        print("deleting file over ftp")
        session.delete(source_name)
    except:
        print(f"File missing {source_name}. skipping delete")

    print(f"Uploading to FTP {source_name}")
    file = open(source,'rb')                  # file to send
    session.storbinary(f"STOR {source_name}", file)     # send the file
    file.close()
    session.quit()

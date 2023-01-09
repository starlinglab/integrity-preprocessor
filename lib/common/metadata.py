import magic
from copy import deepcopy
import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)) + "/../")
import validate
from zipfile import ZipFile
import json
from warcio.archiveiterator import ArchiveIterator
import logging
import base64

class metadata:

  default_author = {
      "@type": "Organization",
      "identifier": "https://starlinglab.org",
      "name": "Starling Lab",
  }
  default_content = {
      "name": "An archive",
      "mime": "application/object",
      "description": "Archive",
      "author": default_author,
      "extras": {},
      "private": {}
  }

  _content = {}
  def __init__(self) -> None:
    self._content = deepcopy(self.default_content)
  
  def set_mime_from_file(self,sourcePath):
    mime = magic.Magic(mime=True)
    meta_mime_type = mime.from_file(sourcePath)
    self._content["mime"] = meta_mime_type

  def add_extras_key(self,extra):
    content = self._content["extras"]
    for key in extra:
      self._content["extras"][key]=extra[key]

  def add_private_element(self,key,value):    
    self._content["private"][key]=value

  def add_private_key(self,private):
    for key in private:
      self._content["private"][key]=private[key]

  def author(self,author):
    self._content["author"] = author

  def description(self,description):
    self._content["description"] = description

  def validated_signature(self,validated_signature):
    self._content["validatedSignature"]=validated_signature

  def name(self,name):
    self._content["name"] = name

  def createdate_utcfromtimestamp(self,meta_date_created):
    create_datetime = datetime.datetime.utcfromtimestamp(meta_date_created)
    self._content["dateCreated"] = create_datetime.isoformat() + "Z"
    self._content["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

  def set_index(self,index_data):
    if "description" in index_data:
      self._content["description"] = index_data["description"]

    if "name" in index_data:
      self._content["name"] = index_data["name"]

    if "relatedAssetCid" in index_data:
      self._content["relatedAssetCid"] = index_data["relatedAssetCid"]
      
    if "sourceId" in index_data:
      self._content["sourceId"] = index_data["sourceId"]

    if "meta_data_private" in index_data:
      for item in index_data["meta_data_private"]:
        self._content["private"][item] = index_data["meta_data_private"][item]

    if "meta_data_public" in index_data:
      for item in index_data["meta_data_public"]:
        self._content["extras"][item] = index_data["meta_data_public"][item]

  def extract_wacz_user_agent(self,wacz_path):
    with ZipFile(wacz_path, "r") as wacz:
        warc = next((s for s in wacz.namelist() if s.endswith(".warc.gz")), None)
        if warc is None:
            return None

        with wacz.open(warc) as warcf:
            for record in ArchiveIterator(warcf):
                if record.rec_type == "request":
                    return record.http_headers.get_header("User-Agent")
    return None
  def process_wacz(self,wacz_path):
    validator = validate.Wacz(wacz_path)
    if not validator.validate():
     raise Exception("WACZ fails to validate")
    self.validated_signature(validator.validated_sigs_json())
    extras = {}


    # WACZ metadata extraction
    with ZipFile(wacz_path, "r") as wacz:
      d = json.loads(wacz.read("datapackage-digest.json"))
      if "signedData" in d:
          # auth sign data
          if "domain" in d["signedData"]:
              extras["authsignSoftware"] = d["signedData"]["software"]
              extras["authsignDomain"] = d["signedData"]["domain"]
          elif "publicKey" in d["signedData"]:
              extras["localsignSoftware"] = d["signedData"]["software"]
              extras["localsignPublicKey"] = d["signedData"]["publicKey"]
              extras["localsignSignaturey"] = d["signedData"]["signature"]
          else:
              logging.warning(f"{wacz_path} WACZ missing signature")

      user_agent = self.extract_wacz_user_agent(wacz_path)

      d = json.loads(wacz.read("datapackage.json"))
      extras["waczVersion"] = d["wacz_version"]
      extras["software"] = d["software"]
      extras["dateCrawled"] = d["created"]
      if user_agent:
          extras["userAgentCrawled"] = user_agent

      if "title" in d:
          extras["waczTitle"] = d["title"]

      extras["pages"] = {}
      counter = 0
      description_list = []
      if "pages/pages.jsonl" in wacz.namelist():
          with wacz.open("pages/pages.jsonl") as jsonl_file:
              for line in jsonl_file.readlines():
                  d = json.loads(line)
                  if "url" in d:
                      extras["pages"][d["id"]] = d["url"]
                      counter=counter+1
                      if counter < 4:
                        description_list.append(d["url"])
                      if counter == 4:
                        description_list.append(...)            
      else:
          logging.info("Missing pages/pages.jsonl in archive %s", wacz_path)

      pagelist = "[ " + ", ".join(description_list[:3]) + "]"
      ## TODO: add "on 2022-03-29" to name
      self.name("Web archive")
      ## TODO: add  captured using Browsertrix on 2022-03-29 to description
      self.description(f"Authenticated web archive of {pagelist}")
      self.add_extras_key({"wacz":extras})

  def process_proofmode(self,proofmode_path):
    validator = validate.ProofMode(proofmode_path)
    if not validator.validate():
      raise Exception("proofmode zip fails to validate")

    self.validated_signature(validator.validated_sigs_json())
    result={}
    date_create = None
    # ProofMode metadata extraction
    with ZipFile(proofmode_path, "r") as proofmode:

      public_pgp = proofmode.read("pubkey.asc").decode("utf-8")

      for file in proofmode.namelist():      

        # Extract file creation date from zip
        # and create a py datetime opject
        x = proofmode.getinfo(file).date_time
        current_date_create = datetime.datetime(
              x[0], x[1], x[2], x[3], x[4], x[5], 0
        )
        # set the earliest date as created date
        if date_create is None or current_date_create < date_create:
          date_create = current_date_create
          self._content["dateCreate"] = date_create.isoformat()

        if os.path.splitext(file)[1] == ".json" and "batchproof" not in file:

          base_file_name = os.path.splitext(file)[0]
          base_file_name = os.path.splitext(base_file_name)[0]

          with proofmode.open(file) as f:
            json_meta = json.load(f)

          pgp = proofmode.read(base_file_name + ".asc").decode("utf-8")
          source_filename = os.path.basename(json_meta["File Path"])
          file_hash = json_meta["File Hash SHA256"]

          result[source_filename] = {
            "pgpSignature": pgp,
            "pgpPublicKey": public_pgp,
            "sha256hash": file_hash,
            "dateCreate": current_date_create.isoformat(),
            "proofmodeJSON": json_meta,
          } 
      self.add_private_key({"proofmode": result})

  def process_legacy_starling_capture(self,source_filename,metadata_filename, signature_filename):
    meta_method = "Starling Capture"

    private={}
    private["starlingCapture"] = {}
    self.name("Starling Capture authenticated image")
    self.description("Image captured and authenticated using the Starling Capture app")

    # Parse out only the first line, some files come with duplicate lines breaking json format
    with open(metadata_filename) as file_meta:
      lines = file_meta.readlines()
      if len(lines) > 1:
        if lines[0] != lines[1]:
          logging.info(f"{source_filename} - Error lines do not match")
          raise Exception(f"Error in file {metadata_filename}")
      metadata_json = json.loads(lines[0])
      private["starlingCapture"]["metadata"] = metadata_json

    with open(signature_filename) as file_meta:
      # Parse out only the first line, some files come with duplicate lines breaking json format
      lines = file_meta.readlines()
      if len(lines) > 1:
        if lines[0] != lines[1]:
          logging.info(f"{source_filename} - Error lines do not match")
          raise Exception(f"Error in file {signature_filename}")
      signature_json = json.loads(lines[0])
      private["starlingCapture"]["signatures"] = signature_json

    # Legacy metadata bug - workaround    
    metadata_json_fix=deepcopy(metadata_json)
    metadata_json_fix["information"]=[]
    metadata_json_fix=json.dumps(metadata_json_fix)
    metadata_json_fix=metadata_json_fix.replace(" ","")
    sc = validate.StarlingCapture(source_filename, metadata_json_fix, signature_json)
    if not sc.validate():
      raise Exception("Hashes or signatures did not validate")
    validatedSignatures=sc.validated_sigs_json()

    metadata_byte = metadata_json_fix.encode("ascii")
    metadata_base64_bytes = base64.b64encode(metadata_byte)
    base64_string = metadata_base64_bytes.decode("ascii")      

    private["starlingCapture"]["signatures"][0]["b64AuthenticatedMetadata"] = base64_string
    self._content["validatedSignature"]=validatedSignatures
    self.add_private_key(private)

  def get_content(self):
    return self._content
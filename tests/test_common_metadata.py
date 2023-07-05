import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../lib")))
import common


def test_common_metadata():
    md = common.Metadata()
    md.set_mime_from_file("assets/wacz/good/domain-sig.wacz")
    assert md.get_content()["mime"] == "application/zip"

    md.add_extras_key({"test-extra-1": "testing test-extra-1"})
    assert md.get_content()["extras"]["test-extra-1"] == "testing test-extra-1"

    md.add_private_key({"test-private-1": "testing test-private-1"})
    assert md.get_content()["private"]["test-private-1"] == "testing test-private-1"

    md.add_private_element("test-private-2", "testing test-private-2")
    assert md.get_content()["private"]["test-private-2"] == "testing test-private-2"

    test_author = {
        "@type": "Organization",
        "identifier": "https://example.org",
        "name": "This is a test",
    }

    md.author(test_author)
    assert md.get_content()["author"] == test_author

    md.description("testing description")
    assert md.get_content()["description"] == "testing description"

    test_validated_signature = {
        "starling:algorithm": "sig66-ecdsa",
        "starling:authenticatedMessage": "59b0472d9f364988c92f3f7422aa519a19fb5b0b6b4230b3dd72c880d0fc7324803fdcd434e5dc00132eb7daa8b7a01c974f500461adc2ade13b8a1e944b0f75",
        "starling:authenticatedMessageDescription": "SHA256 hash of image data concatenated with SHA256 hash of metadata",
        "starling:provider": "sig66",
        "starling:publicKey": "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAET7ni+KmrI888C4AdywnZ8wdD2eJi\ndS3fFrbeboYbgbULHtdPUKj+RnE4nGSN/C1Px3AaMhgzpy8QyWvVmZZpVQ==\n-----END PUBLIC KEY-----",
        "starling:signature": "MEQCIGFHsn8vsgRqNlNkcsBfvX9qB0XaLCJYOy7wV3uurk7gAiAku+QHCjOxy8ye6d/IWtQCKAZycd3QCtVxCJKj0yzDnA==",
    }
    md.validated_signature(test_validated_signature)
    assert md.get_content()["validatedSignatures"] == test_validated_signature

    md.name("testing name")
    assert md.get_content()["name"] == "testing name"

    md.createdate("2020-02-02")
    assert md.get_content()["dateCreated"] == "2020-02-02"

    md.createdate_utcfromtimestamp(1688160532)
    assert md.get_content()["dateCreated"] == "2023-06-30T21:28:52Z"

    md.set_source_id_dict({"source": "value"})
    assert md.get_content()["sourceId"] == {"source": "value"}

    test_source = {"key": "source_key", "value": "source_value"}
    md.set_source_id("source_key", "source_value")
    assert md.get_content()["sourceId"] == test_source

    test_source = {"key2": "source_key2", "value2": "source_value2"}
    testindex = {
        "description": "index_description",
        "name": "index name",
        "relatedAssetCid": "index related asset",
        "sourceId": test_source,
        "meta_data_private": {"privatekey": "private test"},
        "meta_data_public": {"publickey": "public test"},
    }
    md.set_index(testindex)
    assert md.get_content()["description"] == "index_description"
    assert md.get_content()["name"] == "index name"
    assert md.get_content()["relatedAssetCid"] == "index related asset"
    assert md.get_content()["sourceId"] == test_source
    assert md.get_content()["extras"]["publickey"] == "public test"
    assert md.get_content()["private"]["privatekey"] == "private test"

    final_test = {
        "name": "index name",
        "mime": "application/zip",
        "description": "index_description",
        "author": {
            "@type": "Organization",
            "identifier": "https://example.org",
            "name": "This is a test",
        },
        "extras": {"test-extra-1": "testing test-extra-1", "publickey": "public test"},
        "private": {
            "test-private-1": "testing test-private-1",
            "test-private-2": "testing test-private-2",
            "privatekey": "private test",
        },
        "timestamp": "XXXX",
        "validatedSignatures": {
            "starling:algorithm": "sig66-ecdsa",
            "starling:authenticatedMessage": "59b0472d9f364988c92f3f7422aa519a19fb5b0b6b4230b3dd72c880d0fc7324803fdcd434e5dc00132eb7daa8b7a01c974f500461adc2ade13b8a1e944b0f75",
            "starling:authenticatedMessageDescription": "SHA256 hash of image data concatenated with SHA256 hash of metadata",
            "starling:provider": "sig66",
            "starling:publicKey": "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAET7ni+KmrI888C4AdywnZ8wdD2eJi\ndS3fFrbeboYbgbULHtdPUKj+RnE4nGSN/C1Px3AaMhgzpy8QyWvVmZZpVQ==\n-----END PUBLIC KEY-----",
            "starling:signature": "MEQCIGFHsn8vsgRqNlNkcsBfvX9qB0XaLCJYOy7wV3uurk7gAiAku+QHCjOxy8ye6d/IWtQCKAZycd3QCtVxCJKj0yzDnA==",
        },
        "dateCreated": "2023-06-30T21:28:52Z",
        "sourceId": {"key2": "source_key2", "value2": "source_value2"},
        "relatedAssetCid": "index related asset",
    }
    md.get_content()["timestamp"]="XXXX"
    assert md.get_content() == final_test

    # md.process_wacz
    # md.process_proofmode
    

common_metadata_test()

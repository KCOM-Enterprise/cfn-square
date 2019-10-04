import json
import os.path
import subprocess
import sys
import tempfile

import boto3

from cfn_sphere.template import CloudFormationTemplate
from cfn_sphere.util import get_logger

class CloudFormationSamPackager:
    """
    Run `aws cloudformation package` to upload SAM package artifacts to S3 and
    replace values in template.
    """

    @classmethod
    def package(cls, template_url, working_dir, template, region, package_bucket):
        logger = get_logger()

        if not package_bucket:
            return template

        if template_url.lower().startswith("s3://") or  template_url.lower().startswith("https://"):
            raise Exception("SAM packaging is only supported for local templates (not S3/HTTPS)")

        template_body_dict = template.get_template_body_dict()

        # Save template to a temporary file in the original template's
        # directory. Call `aws cloudformation package` to upload artifacts
        # to S3.
        aws_credentials = boto3.DEFAULT_SESSION.get_credentials()
        with tempfile.NamedTemporaryFile(mode="w",
                                         dir=os.path.dirname(os.path.join(working_dir, template_url)),
                                         suffix=".json") as src_fp:
            # Save the template. Ensure the buffer's flushed to disk before
            # calling `aws cloudformation package`.
            json.dump(template_body_dict, src_fp)
            src_fp.flush()

            # Open temporary file for the packaged template.
            # We'd previously used stdout, but the packaging process also
            # wrote status to stdout when the source artifact changed, causing
            # malformed JSON.
            with tempfile.NamedTemporaryFile(mode="r") as dst_fp:
                logger.info("Packaging {}".format(template_url))
                result = subprocess.check_call(
                    args=[
                        "aws", "cloudformation", "package",
                        "--template-file", src_fp.name,
                        "--s3-bucket", package_bucket,
                        "--output-template-file", dst_fp.name,
                        "--use-json"
                    ],
                    env=dict(
                        os.environ,
                        AWS_REGION=region,
                        AWS_ACCESS_KEY_ID=aws_credentials.access_key,
                        AWS_SECRET_ACCESS_KEY=aws_credentials.secret_key,
                        AWS_SESSION_TOKEN=aws_credentials.token or ''
                    ),
                    stdout=subprocess.DEVNULL,
                    stderr=sys.stderr
                )

                result = dst_fp.read()

        template_body_dict = json.loads(result)
        template = CloudFormationTemplate(template_body_dict, template.name)
        return template

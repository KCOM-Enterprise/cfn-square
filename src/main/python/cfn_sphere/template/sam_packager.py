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
    def package(cls, template, config, stack_config):
        logger = get_logger()

        if not stack_config.package_bucket:
            return template

        if stack_config.template_url.lower().startswith(("s3://", "https://")):
            raise Exception("SAM packaging is only supported for local templates (not S3/HTTPS)")

        template_body_dict = template.get_template_body_dict()

        # Save template to a temporary file in the original template's
        # directory. Call `aws cloudformation package` to upload artifacts
        # to S3.
        aws_credentials = boto3.DEFAULT_SESSION.get_credentials()
        template_path = os.path.dirname(os.path.join(stack_config.working_dir, stack_config.template_url))
        with tempfile.NamedTemporaryFile(mode="w", dir=template_path, suffix=".json") as src_fp:
            # Save the template. Ensure the buffer's flushed to disk before
            # calling `aws cloudformation package`.
            json.dump(template_body_dict, src_fp)
            src_fp.flush()
            
            src_template_filename = src_fp.name

            # Call `sam build` if option is present in config.
            if stack_config.sam_build not in (None, False):
                logger.info("Building {}".format(stack_config.template_url))

                build_path = tempfile.mkdtemp()

                args = [
                    "sam",
                    "build",
                    "--template", src_template_filename,
                    "--build-dir", build_path
                ]
                if stack_config.sam_build is not True:
                    args += list(stack_config.sam_build)

                subprocess.check_call(
                    args=args,
                    env=dict(
                        os.environ,
                        AWS_REGION=config.region,
                        AWS_ACCESS_KEY_ID=aws_credentials.access_key,
                        AWS_SECRET_ACCESS_KEY=aws_credentials.secret_key,
                        AWS_SESSION_TOKEN=aws_credentials.token
                    ),
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )

                src_template_filename = os.path.join(build_path, "template.yaml")

            # Open temporary file for the packaged template.
            # We'd previously used stdout, but the packaging process also
            # wrote status to stdout when the source artifact changed, causing
            # malformed JSON.
            with tempfile.NamedTemporaryFile(mode="r") as dst_fp:
                logger.info("Packaging {}".format(stack_config.template_url))
                subprocess.check_call(
                    args=[
                        "aws", "cloudformation", "package",
                        "--template-file", src_template_filename,
                        "--s3-bucket", stack_config.package_bucket,
                        "--output-template-file", dst_fp.name,
                        "--use-json"
                    ],
                    env=dict(
                        os.environ,
                        AWS_REGION=config.region,
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

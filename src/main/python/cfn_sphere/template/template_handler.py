from cfn_sphere.file_loader import FileLoader
from cfn_sphere.template.sam_packager import CloudFormationSamPackager
from cfn_sphere.template.transformer import CloudFormationTemplateTransformer
from cfn_sphere.util import get_git_repository_remote_url


class TemplateHandler(object):
    @staticmethod
    def get_template(config, stack_config):
        template = FileLoader.get_cloudformation_template(
            stack_config.template_url,
            stack_config.working_dir
        )
        additional_stack_description = "Config repo url: {0}".format(
            get_git_repository_remote_url(stack_config.working_dir)
        )
        template = CloudFormationTemplateTransformer.transform_template(
            template,
            additional_stack_description
        )
        template = CloudFormationSamPackager.package(
            template,
            config,
            stack_config
        )
        return template
